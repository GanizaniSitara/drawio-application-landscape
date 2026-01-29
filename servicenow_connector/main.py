#!/usr/bin/env python3
"""
ServiceNow Connector for Application Landscape Diagrams.

This script downloads business application data from ServiceNow and transforms
it to the CSV format expected by the Draw.io Application Landscape generator.

Usage:
    # Download and transform in one step
    python -m servicenow_connector.main download --url "https://yourcompany.service-now.com/report..."

    # Just transform an existing file
    python -m servicenow_connector.main transform --input export.csv --output applications.csv

    # Interactive mode (opens browser for SSO login)
    python -m servicenow_connector.main interactive
"""
import argparse
import sys
from pathlib import Path

from .config import config, ENV_TEMPLATE
from .browser import run_download, ServiceNowBrowser
from .transformer import DataTransformer


def cmd_download(args):
    """Download data from ServiceNow."""
    url = args.url or config.report_url or config.export_url

    if not url:
        print("Error: No URL provided. Use --url or set SERVICENOW_REPORT_URL in .env")
        return 1

    output_dir = Path(args.output) if args.output else Path(config.output_dir)

    print(f"ServiceNow Connector")
    print(f"=" * 50)
    print(f"URL: {url}")
    print(f"Output directory: {output_dir}")
    print(f"Headless mode: {args.headless}")

    # Download the file
    downloaded_path = run_download(url, str(output_dir), args.headless)

    if not downloaded_path:
        print("\nDownload failed. Please check the URL and try again.")
        return 1

    # Transform if requested
    if args.transform:
        print(f"\nTransforming downloaded file...")
        transformer = DataTransformer()
        output_path = output_dir / f"Application_Diagram_Builder.csv"
        transformer.transform_file(downloaded_path, output_path, args.type)
        print(f"Transformed data saved to: {output_path}")

    return 0


def cmd_transform(args):
    """Transform an existing ServiceNow export file."""
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    output_path = Path(args.output) if args.output else None

    print(f"ServiceNow Data Transformer")
    print(f"=" * 50)
    print(f"Input: {input_path}")
    print(f"Type: {args.type}")

    transformer = DataTransformer()
    result_path = transformer.transform_file(input_path, output_path, args.type)

    print(f"\nTransformation complete: {result_path}")
    return 0


def cmd_interactive(args):
    """Interactive mode - open browser and let user navigate."""
    import asyncio

    async def run_interactive():
        instance_url = args.url or config.instance_url

        if not instance_url:
            print("Error: No instance URL provided. Use --url or set SERVICENOW_INSTANCE_URL in .env")
            return 1

        print(f"ServiceNow Interactive Mode")
        print(f"=" * 50)
        print(f"Instance: {instance_url}")
        print()
        print("A browser window will open. Please:")
        print("1. Complete SSO authentication if prompted")
        print("2. Navigate to the report you want to export")
        print("3. Use the export button in ServiceNow to download the data")
        print("4. Close the browser when done")
        print()

        output_dir = Path(args.output) if args.output else Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        async with ServiceNowBrowser(headless=False) as browser:
            # Set up download path
            await browser.context.set_default_timeout(0)  # No timeout in interactive mode

            # Navigate to ServiceNow
            print("Opening browser...")
            await browser.page.goto(instance_url)

            print("\nBrowser session is active.")
            print(f"Downloads will be saved to: {output_dir}")
            print("Press Ctrl+C when done...")

            # Set download behavior
            client = await browser.context.new_cdp_session(browser.page)
            await client.send('Browser.setDownloadBehavior', {
                'behavior': 'allowAndName',
                'downloadPath': str(output_dir.absolute()),
                'eventsEnabled': True
            })

            # Keep browser open until user closes it or Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
                    # Check if page is still open
                    if browser.page.is_closed():
                        break
            except KeyboardInterrupt:
                print("\nClosing browser...")

        print("Session ended.")
        return 0

    return asyncio.run(run_interactive())


def cmd_init(args):
    """Initialize configuration by creating a .env template."""
    env_path = Path(args.output) if args.output else Path('.env.example')

    if env_path.exists() and not args.force:
        print(f"File already exists: {env_path}")
        print("Use --force to overwrite")
        return 1

    env_path.write_text(ENV_TEMPLATE.strip())
    print(f"Created configuration template: {env_path}")
    print("\nNext steps:")
    print(f"1. Copy {env_path} to .env")
    print("2. Edit .env with your ServiceNow details")
    print("3. Run: python -m servicenow_connector.main download")
    return 0


def cmd_test_connection(args):
    """Test connection to ServiceNow."""
    import asyncio

    async def test():
        url = args.url or config.instance_url

        if not url:
            print("Error: No URL provided. Use --url or set SERVICENOW_INSTANCE_URL in .env")
            return 1

        print(f"Testing connection to: {url}")

        async with ServiceNowBrowser(headless=False) as browser:
            success = await browser.authenticate(url)

            if success:
                print("\n✓ Connection successful!")
                print("Browser session and cookies have been saved.")
                print("Future downloads may not require re-authentication.")
                return 0
            else:
                print("\n✗ Connection failed")
                return 1

    return asyncio.run(test())


def main():
    parser = argparse.ArgumentParser(
        description='ServiceNow Connector for Application Landscape Diagrams',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize configuration
  python -m servicenow_connector.main init

  # Test connection (opens browser for SSO)
  python -m servicenow_connector.main test --url https://yourcompany.service-now.com

  # Download from a report URL
  python -m servicenow_connector.main download --url "https://yourcompany.service-now.com/sys_report..."

  # Download and auto-transform
  python -m servicenow_connector.main download --url "..." --transform

  # Transform an existing export file
  python -m servicenow_connector.main transform --input servicenow_export.csv

  # Interactive mode
  python -m servicenow_connector.main interactive
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Create configuration template')
    init_parser.add_argument('--output', '-o', help='Output path for template')
    init_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing file')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test connection to ServiceNow')
    test_parser.add_argument('--url', '-u', help='ServiceNow instance URL')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download data from ServiceNow')
    download_parser.add_argument('--url', '-u', help='Report or export URL')
    download_parser.add_argument('--output', '-o', help='Output directory')
    download_parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    download_parser.add_argument('--transform', '-t', action='store_true', help='Transform after download')
    download_parser.add_argument('--type', choices=['applications', 'capabilities'],
                                 default='applications', help='Output type (default: applications)')

    # Transform command
    transform_parser = subparsers.add_parser('transform', help='Transform existing export file')
    transform_parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    transform_parser.add_argument('--output', '-o', help='Output CSV file')
    transform_parser.add_argument('--type', choices=['applications', 'capabilities'],
                                  default='applications', help='Output type (default: applications)')

    # Interactive command
    interactive_parser = subparsers.add_parser('interactive',
                                                help='Interactive mode - browse and download manually')
    interactive_parser.add_argument('--url', '-u', help='ServiceNow instance URL')
    interactive_parser.add_argument('--output', '-o', help='Output directory for downloads')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Validate configuration
    errors = config.validate()
    if errors and args.command not in ['init', 'test']:
        if not (hasattr(args, 'url') and args.url):
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nRun 'python -m servicenow_connector.main init' to create a configuration template")
            return 1

    # Execute command
    commands = {
        'init': cmd_init,
        'test': cmd_test_connection,
        'download': cmd_download,
        'transform': cmd_transform,
        'interactive': cmd_interactive,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
