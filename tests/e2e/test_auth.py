"""Authentication flow E2E tests."""

from playwright.sync_api import Page, expect


class TestLogin:
    """Tests for the login flow."""

    def test_login_page_loads(self, page: Page, base_url: str):
        """Test that the login page loads correctly."""
        page.goto(f"{base_url}/login")

        # Check page title
        expect(page).to_have_title("Login - Blu")

        # Check for password input
        password_input = page.locator('input[type="password"]')
        expect(password_input).to_be_visible()

        # Check for submit button
        submit_button = page.locator('button[type="submit"]')
        expect(submit_button).to_be_visible()
        expect(submit_button).to_have_text("Login")

    def test_redirect_to_login_when_unauthenticated(self, page: Page, base_url: str):
        """Test that unauthenticated users are redirected to login."""
        page.goto(f"{base_url}/")

        # Should redirect to login
        expect(page).to_have_url(f"{base_url}/login")

    def test_login_with_invalid_password(self, page: Page, base_url: str):
        """Test login with invalid password shows error."""
        page.goto(f"{base_url}/login")

        # Enter wrong password
        page.fill('input[type="password"]', "wrongpassword")
        page.click('button[type="submit"]')

        # Should show error message
        error_message = page.locator(".error-message")
        expect(error_message).to_be_visible()
        expect(error_message).to_contain_text("Invalid password")

    def test_login_with_valid_password(self, authenticated_page: Page, base_url: str):
        """Test successful login redirects to main page."""
        # authenticated_page fixture handles login
        expect(authenticated_page).to_have_url(f"{base_url}/")

    def test_logout(self, authenticated_page: Page, base_url: str):
        """Test logout functionality."""
        # Click logout link
        authenticated_page.click('a[href="/logout"]')

        # Should redirect to login
        expect(authenticated_page).to_have_url(f"{base_url}/login")


class TestRateLimiting:
    """Tests for login rate limiting."""

    def test_rate_limiting_after_failed_attempts(self, page: Page, base_url: str):
        """Test that rate limiting kicks in after multiple failed attempts."""
        page.goto(f"{base_url}/login")

        # Try multiple wrong passwords
        for i in range(6):  # Should trigger rate limit after 5
            page.fill('input[type="password"]', f"wrong{i}")
            page.click('button[type="submit"]')
            page.wait_for_timeout(500)  # Small delay between attempts

        # Should see rate limiting message
        error_message = page.locator(".error-message")
        expect(error_message).to_be_visible()
        # Message should mention locked out or try again
        expect(error_message).to_contain_text("locked", ignore_case=True)
