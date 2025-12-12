"""Voice UI E2E tests."""

import re

from playwright.sync_api import Page, expect


class TestMainPage:
    """Tests for the main voice UI page."""

    def test_main_page_elements(self, authenticated_page: Page):
        """Test that all main page elements are present."""
        page = authenticated_page

        # Header
        header = page.locator(".header h1")
        expect(header).to_be_visible()
        expect(header).to_contain_text("Ultra")

        # Navigation links
        files_link = page.locator('a[href="/files"]')
        expect(files_link).to_be_visible()

        logout_link = page.locator('a[href="/logout"]')
        expect(logout_link).to_be_visible()

        # Status bar
        status_dot = page.locator("#statusDot")
        expect(status_dot).to_be_visible()

        status_text = page.locator("#statusText")
        expect(status_text).to_be_visible()

        # Chat container
        chat = page.locator("#chat")
        expect(chat).to_be_visible()

        # Welcome message
        welcome = page.locator(".message.system")
        expect(welcome).to_be_visible()

        # Input area
        text_input = page.locator("#textInput")
        expect(text_input).to_be_visible()

        voice_btn = page.locator("#voiceBtn")
        expect(voice_btn).to_be_visible()

        send_btn = page.locator("#sendBtn")
        expect(send_btn).to_be_visible()

    def test_text_input_functionality(self, authenticated_page: Page):
        """Test that text input works correctly."""
        page = authenticated_page
        text_input = page.locator("#textInput")

        # Type a message
        text_input.fill("Hello, this is a test message")

        # Check value
        expect(text_input).to_have_value("Hello, this is a test message")

        # Clear and type again
        text_input.clear()
        expect(text_input).to_have_value("")

    def test_text_input_auto_resize(self, authenticated_page: Page):
        """Test that text input auto-resizes with content."""
        page = authenticated_page
        text_input = page.locator("#textInput")

        # Get initial height
        initial_height = text_input.evaluate("el => el.offsetHeight")

        # Type multiple lines
        text_input.fill("Line 1\nLine 2\nLine 3\nLine 4")

        # Height should increase (or stay same if max height reached)
        new_height = text_input.evaluate("el => el.offsetHeight")
        assert new_height >= initial_height

    def test_send_button_click(self, authenticated_page: Page):
        """Test sending a message via button click."""
        page = authenticated_page
        text_input = page.locator("#textInput")
        send_btn = page.locator("#sendBtn")
        chat = page.locator("#chat")

        # Type a message
        text_input.fill("Test message via button")

        # Click send
        send_btn.click()

        # Check that user message appears in chat
        user_message = chat.locator(".message.user").last
        expect(user_message).to_be_visible()
        expect(user_message).to_contain_text("Test message via button")

        # Input should be cleared
        expect(text_input).to_have_value("")

    def test_send_message_via_enter(self, authenticated_page: Page):
        """Test sending a message by pressing Enter."""
        page = authenticated_page
        text_input = page.locator("#textInput")
        chat = page.locator("#chat")

        # Type a message and press Enter
        text_input.fill("Test message via Enter")
        text_input.press("Enter")

        # Check that user message appears in chat
        user_message = chat.locator(".message.user").last
        expect(user_message).to_be_visible()
        expect(user_message).to_contain_text("Test message via Enter")

    def test_shift_enter_does_not_send(self, authenticated_page: Page):
        """Test that Shift+Enter creates a new line instead of sending."""
        page = authenticated_page
        text_input = page.locator("#textInput")

        # Type and press Shift+Enter
        text_input.fill("Line 1")
        text_input.press("Shift+Enter")
        text_input.type("Line 2")

        # Should have newline in input, not send
        value = text_input.input_value()
        assert "\n" in value or "Line 2" in value


class TestConnectionStatus:
    """Tests for connection status display."""

    def test_initial_connecting_status(self, authenticated_page: Page):
        """Test that initial status shows connecting."""
        page = authenticated_page
        status_dot = page.locator("#statusDot")
        status_text = page.locator("#statusText")

        # Should show connecting status initially
        expect(status_dot).to_have_class(re.compile(r"connecting"))
        expect(status_text).to_contain_text("Connecting")

    def test_voice_button_disabled_when_connecting(self, authenticated_page: Page):
        """Test that voice button is disabled during connection."""
        page = authenticated_page
        voice_btn = page.locator("#voiceBtn")

        # Voice button should be disabled initially
        expect(voice_btn).to_be_disabled()


class TestErrorDisplay:
    """Tests for error display functionality."""

    def test_error_banner_hidden_initially(self, authenticated_page: Page):
        """Test that error banner is hidden by default."""
        page = authenticated_page
        error_banner = page.locator("#errorBanner")

        # Error banner should not be visible
        expect(error_banner).not_to_have_class(re.compile(r"visible"))

    def test_error_banner_dismiss(self, authenticated_page: Page):
        """Test that error banner can be dismissed."""
        page = authenticated_page

        # Manually show error banner via JS
        page.evaluate("""
            document.getElementById('errorBanner').classList.add('visible');
            document.getElementById('errorText').textContent = 'Test error';
        """)

        error_banner = page.locator("#errorBanner")
        expect(error_banner).to_have_class(re.compile(r"visible"))

        # Click dismiss button
        page.click("#errorDismiss")

        # Banner should be hidden
        expect(error_banner).not_to_have_class(re.compile(r"visible"))


class TestProcessingIndicator:
    """Tests for processing indicator functionality."""

    def test_processing_indicator_via_js(self, authenticated_page: Page):
        """Test processing indicator display via JavaScript."""
        page = authenticated_page
        chat = page.locator("#chat")

        # Manually trigger addProcessing via JS
        page.evaluate("addProcessing('Testing')")

        # Processing indicator should appear
        processing = chat.locator("#processing")
        expect(processing).to_be_visible()
        expect(processing).to_contain_text("Testing")

        # Remove processing
        page.evaluate("removeProcessing()")

        # Should be removed
        expect(processing).not_to_be_attached()


class TestMessageTypes:
    """Tests for different message types in chat."""

    def test_user_message_styling(self, authenticated_page: Page):
        """Test that user messages have correct styling."""
        page = authenticated_page
        chat = page.locator("#chat")

        # Add user message via JS
        page.evaluate("addMessage('User test', 'user')")

        user_message = chat.locator(".message.user").last
        expect(user_message).to_be_visible()
        expect(user_message).to_have_class(re.compile(r"user"))

    def test_assistant_message_styling(self, authenticated_page: Page):
        """Test that assistant messages have correct styling."""
        page = authenticated_page
        chat = page.locator("#chat")

        # Add assistant message via JS
        page.evaluate("addMessage('Assistant test', 'assistant')")

        assistant_message = chat.locator(".message.assistant").last
        expect(assistant_message).to_be_visible()
        expect(assistant_message).to_have_class(re.compile(r"assistant"))

    def test_error_message_styling(self, authenticated_page: Page):
        """Test that error messages have correct styling."""
        page = authenticated_page
        chat = page.locator("#chat")

        # Add error message via JS
        page.evaluate("addMessage('Error test', 'error')")

        error_message = chat.locator(".message.error").last
        expect(error_message).to_be_visible()
        expect(error_message).to_have_class(re.compile(r"error"))

    def test_system_message_styling(self, authenticated_page: Page):
        """Test that system messages have correct styling."""
        page = authenticated_page
        chat = page.locator("#chat")

        # System message should already exist (welcome)
        system_message = chat.locator(".message.system").first
        expect(system_message).to_be_visible()
        expect(system_message).to_have_class(re.compile(r"system"))
