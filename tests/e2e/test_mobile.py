"""Mobile responsiveness E2E tests."""

import pytest
from playwright.sync_api import Browser, Page, expect


class TestMobileResponsiveness:
    """Tests for mobile device responsiveness."""

    @pytest.fixture
    def mobile_authenticated(self, browser: Browser, base_url: str) -> Page:
        """Return a mobile-sized page that is logged in."""
        import os

        context = browser.new_context(
            viewport={"width": 375, "height": 667},  # iPhone SE
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
        )
        page = context.new_page()

        # Login
        page.goto(f"{base_url}/login")
        page.fill('input[type="password"]', os.getenv("TEST_PASSWORD", "test123"))
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/")

        yield page
        context.close()

    def test_mobile_viewport_renders(self, mobile_authenticated: Page):
        """Test that page renders correctly on mobile viewport."""
        page = mobile_authenticated

        # All main elements should be visible
        expect(page.locator(".header")).to_be_visible()
        expect(page.locator("#chat")).to_be_visible()
        expect(page.locator(".input-area")).to_be_visible()
        expect(page.locator("#textInput")).to_be_visible()
        expect(page.locator("#voiceBtn")).to_be_visible()
        expect(page.locator("#sendBtn")).to_be_visible()

    def test_mobile_buttons_tap_target_size(self, mobile_authenticated: Page):
        """Test that buttons have adequate tap target size for mobile."""
        page = mobile_authenticated

        # Voice button should be at least 44x44 (Apple's minimum)
        voice_btn = page.locator("#voiceBtn")
        box = voice_btn.bounding_box()
        assert box is not None
        assert box["width"] >= 44, f"Voice button width {box['width']} is less than 44px"
        assert box["height"] >= 44, f"Voice button height {box['height']} is less than 44px"

        # Send button should be at least 44x44
        send_btn = page.locator("#sendBtn")
        box = send_btn.bounding_box()
        assert box is not None
        assert box["width"] >= 44, f"Send button width {box['width']} is less than 44px"
        assert box["height"] >= 44, f"Send button height {box['height']} is less than 44px"

    def test_mobile_text_input_visible(self, mobile_authenticated: Page):
        """Test that text input is usable on mobile."""
        page = mobile_authenticated
        text_input = page.locator("#textInput")

        # Should be visible and tappable
        expect(text_input).to_be_visible()

        # Check font size is at least 16px (prevents iOS zoom)
        font_size = text_input.evaluate("el => getComputedStyle(el).fontSize")
        size_value = int(font_size.replace("px", ""))
        assert size_value >= 16, f"Font size {size_value}px may cause iOS zoom on focus"

    def test_mobile_chat_scrollable(self, mobile_authenticated: Page):
        """Test that chat container is scrollable on mobile."""
        page = mobile_authenticated
        chat = page.locator("#chat")

        # Add multiple messages to overflow
        for i in range(20):
            page.evaluate(f"addMessage('Test message {i}', 'assistant')")

        # Chat should be scrollable
        scroll_height = chat.evaluate("el => el.scrollHeight")
        client_height = chat.evaluate("el => el.clientHeight")
        assert scroll_height > client_height, "Chat should be scrollable with many messages"

    def test_mobile_input_area_sticky(self, mobile_authenticated: Page):
        """Test that input area stays visible at bottom on mobile."""
        page = mobile_authenticated

        # Add messages to make page scrollable
        for i in range(20):
            page.evaluate(f"addMessage('Test message {i}', 'assistant')")

        # Input area should still be visible
        input_area = page.locator(".input-area")
        expect(input_area).to_be_visible()
        expect(input_area).to_be_in_viewport()

    def test_mobile_message_width(self, mobile_authenticated: Page):
        """Test that messages don't overflow on mobile."""
        page = mobile_authenticated
        chat = page.locator("#chat")

        # Add a long message
        long_message = "This is a very long message " * 10
        page.evaluate(f"addMessage('{long_message}', 'user')")

        # Message should wrap and not overflow
        message = chat.locator(".message.user").last
        box = message.bounding_box()
        viewport = page.viewport_size

        assert box is not None
        assert viewport is not None
        assert box["width"] <= viewport["width"], "Message should not overflow viewport"


class TestTabletResponsiveness:
    """Tests for tablet device responsiveness."""

    @pytest.fixture
    def tablet_authenticated(self, browser: Browser, base_url: str) -> Page:
        """Return a tablet-sized page that is logged in."""
        import os

        context = browser.new_context(
            viewport={"width": 768, "height": 1024},  # iPad
            user_agent="Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)",
        )
        page = context.new_page()

        # Login
        page.goto(f"{base_url}/login")
        page.fill('input[type="password"]', os.getenv("TEST_PASSWORD", "test123"))
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/")

        yield page
        context.close()

    def test_tablet_layout(self, tablet_authenticated: Page):
        """Test that tablet layout is appropriate."""
        page = tablet_authenticated

        # Chat should have max-width on larger screens
        chat = page.locator("#chat")
        box = chat.bounding_box()
        viewport = page.viewport_size

        assert box is not None
        assert viewport is not None
        # On tablet, chat might be centered with max-width
        # Just verify it's visible and reasonably sized
        assert box["width"] > 300, "Chat should have reasonable width on tablet"


class TestDesktopResponsiveness:
    """Tests for desktop responsiveness."""

    @pytest.fixture
    def desktop_authenticated(self, browser: Browser, base_url: str) -> Page:
        """Return a desktop-sized page that is logged in."""
        import os

        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Login
        page.goto(f"{base_url}/login")
        page.fill('input[type="password"]', os.getenv("TEST_PASSWORD", "test123"))
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/")

        yield page
        context.close()

    def test_desktop_chat_max_width(self, desktop_authenticated: Page):
        """Test that chat has appropriate max-width on desktop."""
        page = desktop_authenticated
        chat = page.locator("#chat")

        # Chat should have max-width to improve readability
        max_width = chat.evaluate("el => getComputedStyle(el).maxWidth")
        assert max_width != "none", "Chat should have max-width on desktop for readability"

    def test_desktop_message_width(self, desktop_authenticated: Page):
        """Test that messages have appropriate max-width on desktop."""
        page = desktop_authenticated
        chat = page.locator("#chat")

        # Add a message
        page.evaluate("addMessage('Test desktop message', 'user')")

        message = chat.locator(".message.user").last
        box = message.bounding_box()
        viewport = page.viewport_size

        assert box is not None
        assert viewport is not None
        # Message should be constrained, not full width
        assert box["width"] < viewport["width"] * 0.8, "Messages should not be too wide on desktop"
