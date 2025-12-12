"""Pytest fixtures for Playwright E2E tests."""

import os

import pytest
from playwright.sync_api import Browser, Page

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test123")


@pytest.fixture(scope="session")
def base_url() -> str:
    """Get the base URL for testing."""
    return BASE_URL


@pytest.fixture
def authenticated_page(page: Page, base_url: str) -> Page:
    """Return a page that is already logged in."""
    # Go to login page
    page.goto(f"{base_url}/login")

    # Fill in password and submit
    page.fill('input[type="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')

    # Wait for redirect to main page
    page.wait_for_url(f"{base_url}/")

    return page


@pytest.fixture
def mobile_page(browser: Browser, base_url: str) -> Page:
    """Return a mobile-sized browser context."""
    context = browser.new_context(
        viewport={"width": 375, "height": 667},  # iPhone SE size
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
    )
    page = context.new_page()
    yield page
    context.close()
