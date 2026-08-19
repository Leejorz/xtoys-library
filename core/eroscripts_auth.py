from pathlib import Path
import os

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


class EroScriptsAuth:

    LOGIN_URL = "https://discuss.eroscripts.com/login"

    def __init__(self, root: Path):

        self.root = root

        self.session_dir = (
            root / "cache" / "eroscripts_session"
        )

        self.session_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None

    def start(self):

        browser_dir = self.root / "playwright-browsers"
        if browser_dir.exists():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_dir)

        self.playwright = sync_playwright().start()

        self.context = (
            self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=False
            )
        )

        return self.context

    def login(self, confirmation_callback=None):

        if self.context is None:
            self.start()

        page = self.context.pages[0] if self.context.pages else (
            self.context.new_page()
        )

        page.goto(
            self.LOGIN_URL,
            wait_until="domcontentloaded"
        )

        print()
        print("=" * 50)
        print("EroScripts Login")
        print("=" * 50)
        print()
        print(
            "A browser window has been opened."
        )
        print(
            "Log into EroScripts normally."
        )
        print(
            "Enter your authenticator code when requested."
        )
        print()
        if confirmation_callback is None:
            print(
                "When you have successfully logged in,"
            )
            print(
                "return here and press ENTER."
            )
            print()
            input("Press ENTER after login is complete... ")
        else:
            confirmed = confirmation_callback()
            if not confirmed:
                return False

        if not self.is_logged_in(page):

            raise RuntimeError(
                "EroScripts login could not be verified."
            )

        print()
        print(
            "EroScripts login successful."
        )

        return True

    def is_logged_in(self, page: Page | None = None):

        if self.context is None:
            return False

        if page is None:

            if not self.context.pages:
                return False

            page = self.context.pages[0]

        current_url = page.url.lower()

        if "/login" in current_url:
            return False

        return True

    def open_page(self, url: str):

        if self.context is None:
            self.start()

        page = (
            self.context.pages[0]
            if self.context.pages
            else self.context.new_page()
        )

        page.goto(
            url,
            wait_until="domcontentloaded"
        )

        if not self.is_logged_in(page):

            raise RuntimeError(
                "EroScripts authentication is required. "
                "Please log in again."
            )

        return page

    def close(self):

        if self.context is not None:

            self.context.close()
            self.context = None

        if self.playwright is not None:

            self.playwright.stop()
            self.playwright = None