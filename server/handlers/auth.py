"""Authentication handlers."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from server.config import Settings, get_settings
from server.services.auth import AuthService, get_auth_service

router = APIRouter()

SESSION_COOKIE = "aipa_session"


def get_client_ip(request: Request) -> str:
    """Get client IP, handling proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_session_token(request: Request) -> str | None:
    """Get session token from cookie."""
    return request.cookies.get(SESSION_COOKIE)


async def require_auth(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> bool:
    """Dependency that requires authentication (returns 401 for API endpoints)."""
    token = get_session_token(request)
    if not token or not auth.verify_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return True


async def require_auth_redirect(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> bool:
    """Dependency that requires authentication (redirects to login for HTML pages)."""
    token = get_session_token(request)
    if not token or not auth.verify_session(token):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )
    return True


@router.get("/login")
async def login_page(
    request: Request,
    error: str = "",
    auth: AuthService = Depends(get_auth_service),
) -> HTMLResponse:
    """Render login page."""
    # If already logged in, redirect to home
    token = get_session_token(request)
    if token and auth.verify_session(token):
        return RedirectResponse(url="/", status_code=302)

    error_html = ""
    if error:
        error_html = f'<div class="error">{error}</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Blu</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e8e8e8;
        }}
        .login-box {{
            background: rgba(255,255,255,0.1);
            padding: 2rem;
            border-radius: 1rem;
            width: 100%;
            max-width: 320px;
            backdrop-filter: blur(10px);
        }}
        h1 {{
            text-align: center;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }}
        .error {{
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            font-size: 0.875rem;
            text-align: center;
        }}
        input {{
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 0.5rem;
            background: rgba(255,255,255,0.1);
            color: #e8e8e8;
            font-size: 1rem;
            margin-bottom: 1rem;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        button {{
            width: 100%;
            padding: 0.75rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 0.5rem;
            color: white;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        button:hover {{ transform: scale(1.02); }}
        button:active {{ transform: scale(0.98); }}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Blu</h1>
        {error_html}
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="Password" autofocus required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/login")
async def login(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Process login."""
    form = await request.form()
    password = form.get("password", "")
    ip = get_client_ip(request)

    success, result = auth.check_password(str(password), ip)

    if success:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=result,
            httponly=True,
            secure=settings.is_production,  # Only require HTTPS in production
            samesite="lax",  # Allow cookie on redirects
            max_age=86400,  # 24 hours
        )
        return response

    # Failed - redirect to login with error
    return RedirectResponse(
        url=f"/login?error={result}",
        status_code=302,
    )


@router.get("/logout")
async def logout(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> Response:
    """Logout and clear session."""
    token = get_session_token(request)
    if token:
        auth.invalidate_session(token)

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response
