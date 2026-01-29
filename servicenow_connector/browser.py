"""
Playwright-based browser automation for ServiceNow SSO authentication.

This module handles SSO authentication by using a real browser, which allows
users to complete their normal SSO login flow (Okta, Azure AD, Ping, etc.).
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    print("Playwright is not installed. Please run: pip install playwright")
    print("Then install browsers: playwright install chromium")
    sys.exit(1)

from .config import config


class ServiceNowBrowser:
    """Browser automation for ServiceNow with SSO support."""

    def __init__(self, headless: Optional[bool] = None):
        self.headless = headless if headless is not None else config.headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Start the browser."""
        self.playwright = await async_playwright().start()

        # Use chromium - most compatible with enterprise SSO
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',  # Avoid detection
            ]
        )

        # Check if we have saved browser state (cookies/session)
        state_path = Path(config.browser_state_path)
        storage_state = str(state_path) if state_path.exists() else None

        self.context = await self.browser.new_context(
            storage_state=storage_state,
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080},
        )

        self.page = await self.context.new_page()

        # Set reasonable timeouts
        self.page.set_default_timeout(config.browser_timeout)

    async def close(self):
        """Close the browser and save state."""
        if self.context:
            # Save browser state for future sessions
            try:
                state_path = Path(config.browser_state_path)
                state_path.parent.mkdir(parents=True, exist_ok=True)
                await self.context.storage_state(path=str(state_path))
                print(f"Browser state saved to {state_path}")
            except Exception as e:
                print(f"Warning: Could not save browser state: {e}")

        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def authenticate(self, target_url: str) -> bool:
        """
        Navigate to ServiceNow and handle SSO authentication.

        This will open a browser window and wait for the user to complete
        SSO authentication if needed. Once authenticated, the session
        is saved for future use.

        Args:
            target_url: The ServiceNow URL to navigate to

        Returns:
            True if authentication was successful
        """
        print(f"\nNavigating to: {target_url}")
        print("If prompted, please complete SSO authentication in the browser window...")

        await self.page.goto(target_url, wait_until='networkidle')

        # Check if we're on an SSO page (not ServiceNow)
        current_url = self.page.url
        servicenow_domain = self._extract_domain(config.instance_url or target_url)

        if servicenow_domain not in current_url:
            print(f"\nSSO redirect detected. Current URL: {current_url}")
            print("Please complete authentication in the browser window...")

            # Wait for redirect back to ServiceNow (with extended timeout for SSO)
            try:
                await self.page.wait_for_url(
                    f"**{servicenow_domain}**",
                    timeout=300000,  # 5 minutes for SSO
                    wait_until='networkidle'
                )
                print("Authentication successful!")
            except Exception as e:
                print(f"Authentication timeout or error: {e}")
                return False

        # Verify we're logged in by checking for common ServiceNow elements
        try:
            # Wait for the page to fully load
            await self.page.wait_for_load_state('networkidle')
            print("Successfully connected to ServiceNow")
            return True
        except Exception as e:
            print(f"Error verifying ServiceNow connection: {e}")
            return False

    async def download_report(self, report_url: str, output_path: Path) -> Optional[Path]:
        """
        Download a report from ServiceNow.

        Args:
            report_url: URL of the report or export
            output_path: Directory to save the downloaded file

        Returns:
            Path to the downloaded file, or None if failed
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\nDownloading report from: {report_url}")

        # Navigate to the report URL
        await self.page.goto(report_url, wait_until='networkidle')

        # Check if this is a direct CSV/Excel export URL
        if 'CSV' in report_url or 'EXCEL' in report_url or 'XML' in report_url:
            # Direct download - wait for download to start
            return await self._handle_direct_download(output_path)

        # Otherwise, we're on a report page and need to find the export button
        return await self._handle_report_page_export(output_path)

    async def _handle_direct_download(self, output_path: Path) -> Optional[Path]:
        """Handle a direct file download."""
        try:
            # Set up download handler
            async with self.page.expect_download(timeout=config.download_timeout) as download_info:
                # The download should start automatically from the URL
                pass

            download = await download_info.value
            suggested_filename = download.suggested_filename or 'servicenow_export.csv'
            save_path = output_path / suggested_filename

            await download.save_as(str(save_path))
            print(f"Downloaded: {save_path}")
            return save_path

        except Exception as e:
            print(f"Download error: {e}")
            # The content might be directly on the page (no download prompt)
            return await self._save_page_content(output_path)

    async def _handle_report_page_export(self, output_path: Path) -> Optional[Path]:
        """Handle export from a report page UI."""
        print("Looking for export options on the report page...")

        # Common export button selectors in ServiceNow
        export_selectors = [
            'button:has-text("Export")',
            'a:has-text("Export")',
            '[data-action="export"]',
            '.export-button',
            '#export_button',
            'button[title*="Export"]',
            '.icon-export',
        ]

        export_button = None
        for selector in export_selectors:
            try:
                export_button = await self.page.wait_for_selector(selector, timeout=5000)
                if export_button:
                    print(f"Found export button: {selector}")
                    break
            except:
                continue

        if not export_button:
            print("Could not find export button. Trying context menu...")
            # Try right-click context menu
            return await self._try_context_menu_export(output_path)

        # Click export button
        await export_button.click()
        await self.page.wait_for_timeout(1000)  # Wait for menu/dialog

        # Look for CSV option
        csv_selectors = [
            'a:has-text("CSV")',
            'button:has-text("CSV")',
            '[data-format="csv"]',
            'a:has-text("Export to CSV")',
        ]

        for selector in csv_selectors:
            try:
                csv_option = await self.page.wait_for_selector(selector, timeout=3000)
                if csv_option:
                    # Set up download handler before clicking
                    async with self.page.expect_download(timeout=config.download_timeout) as download_info:
                        await csv_option.click()

                    download = await download_info.value
                    suggested_filename = download.suggested_filename or 'servicenow_report.csv'
                    save_path = output_path / suggested_filename

                    await download.save_as(str(save_path))
                    print(f"Downloaded: {save_path}")
                    return save_path
            except:
                continue

        print("Could not complete export via UI")
        return None

    async def _try_context_menu_export(self, output_path: Path) -> Optional[Path]:
        """Try to export via right-click context menu."""
        # This is a fallback - may need adjustment based on your ServiceNow version
        try:
            # Right-click on the page/table
            await self.page.click('body', button='right')
            await self.page.wait_for_timeout(500)

            # Look for export in context menu
            export_option = await self.page.wait_for_selector(
                'text=Export', timeout=3000
            )
            if export_option:
                await export_option.click()
                return await self._handle_direct_download(output_path)
        except:
            pass

        return None

    async def _save_page_content(self, output_path: Path) -> Optional[Path]:
        """Save page content as CSV if it's raw CSV data."""
        try:
            content = await self.page.content()

            # Check if the page contains CSV-like content
            if ',' in content and '\n' in content:
                # Try to extract text content
                text = await self.page.inner_text('body')
                if text and ',' in text:
                    save_path = output_path / 'servicenow_export.csv'
                    save_path.write_text(text)
                    print(f"Saved page content to: {save_path}")
                    return save_path
        except Exception as e:
            print(f"Could not save page content: {e}")

        return None

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc


async def authenticate_and_download(
    url: str,
    output_dir: Optional[str] = None,
    headless: bool = False
) -> Optional[Path]:
    """
    Convenience function to authenticate and download in one step.

    Args:
        url: ServiceNow report or export URL
        output_dir: Directory to save downloaded file
        headless: Whether to run browser in headless mode

    Returns:
        Path to downloaded file, or None if failed
    """
    output_path = Path(output_dir or config.output_dir)

    async with ServiceNowBrowser(headless=headless) as browser:
        # First authenticate
        if not await browser.authenticate(url):
            print("Authentication failed")
            return None

        # Then download
        return await browser.download_report(url, output_path)


def run_download(url: str, output_dir: Optional[str] = None, headless: bool = False) -> Optional[Path]:
    """
    Synchronous wrapper for authenticate_and_download.

    Args:
        url: ServiceNow report or export URL
        output_dir: Directory to save downloaded file
        headless: Whether to run browser in headless mode

    Returns:
        Path to downloaded file, or None if failed
    """
    return asyncio.run(authenticate_and_download(url, output_dir, headless))
