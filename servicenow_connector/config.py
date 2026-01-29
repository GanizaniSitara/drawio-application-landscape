"""
Configuration for ServiceNow connector.

You can set these values via environment variables or by creating a .env file.
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class ServiceNowConfig:
    """Configuration for ServiceNow connection."""

    # ServiceNow instance URL (e.g., https://yourcompany.service-now.com)
    instance_url: str = os.getenv('SERVICENOW_INSTANCE_URL', '')

    # Report URL - the full URL to the report you want to download
    # This can be a saved report URL from ServiceNow
    report_url: str = os.getenv('SERVICENOW_REPORT_URL', '')

    # Alternative: Export URL for direct CSV/Excel export
    # Format: https://yourcompany.service-now.com/cmdb_ci_business_app_list.do?CSV&sysparm_query=...
    export_url: str = os.getenv('SERVICENOW_EXPORT_URL', '')

    # Output directory for downloaded files
    output_dir: str = os.getenv('SERVICENOW_OUTPUT_DIR',
                                 str(Path(__file__).parent.parent / 'examples'))

    # Browser settings
    headless: bool = os.getenv('SERVICENOW_HEADLESS', 'false').lower() == 'true'
    browser_timeout: int = int(os.getenv('SERVICENOW_BROWSER_TIMEOUT', '60000'))  # ms

    # Download timeout (for large exports)
    download_timeout: int = int(os.getenv('SERVICENOW_DOWNLOAD_TIMEOUT', '120000'))  # ms

    # Path to store browser state (cookies, session) for reuse
    browser_state_path: str = os.getenv('SERVICENOW_BROWSER_STATE',
                                         str(Path(__file__).parent / '.browser_state'))

    # Column mappings from ServiceNow to expected CSV format
    # These map ServiceNow field names to the output CSV column names
    # Adjust these based on your ServiceNow report columns
    column_mappings: Optional[dict] = None

    def __post_init__(self):
        """Set default column mappings if not provided."""
        if self.column_mappings is None:
            # Default mappings - adjust based on your ServiceNow report
            self.column_mappings = {
                # ServiceNow field -> Output CSV column
                'u_capability_l1': 'Level1',           # Level 1 Capability
                'u_capability_l2': 'Level2',           # Level 2 Capability
                'name': 'AppName',                     # Application Name
                'u_technical_code': 'TC',              # Technical Code
                'u_status_rag': 'StatusRAG',           # RAG Status
                'u_resilience_tier': 'Resilience',     # Resilience Tier
                'u_cloud_percentage': 'HostingPercent', # Cloud %
                'u_hosting_pattern_1': 'HostingPattern1',
                'u_hosting_pattern_2': 'HostingPattern2',
                'u_data_flow_in': 'Arrow1',            # Data flow direction
                'u_data_flow_out': 'Arrow2',
                'u_link': 'Link',                      # Link URL
                'u_controls_link': 'Controls',         # Controls link
                'u_decommission_date': 'DecommDate',   # Decommission date
            }

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.instance_url and not self.report_url and not self.export_url:
            errors.append("Either SERVICENOW_INSTANCE_URL, SERVICENOW_REPORT_URL, or SERVICENOW_EXPORT_URL must be set")
        return errors


# Global config instance
config = ServiceNowConfig()


# Example .env file content (for documentation)
ENV_TEMPLATE = """
# ServiceNow Connector Configuration
# Copy this to .env and fill in your values

# Your ServiceNow instance URL
SERVICENOW_INSTANCE_URL=https://yourcompany.service-now.com

# Option 1: Report URL (navigate to the report page and copy the URL)
SERVICENOW_REPORT_URL=https://yourcompany.service-now.com/sys_report_template.do?...

# Option 2: Direct export URL (for list exports)
# Go to a list view, right-click "Export" and copy the CSV export link
SERVICENOW_EXPORT_URL=https://yourcompany.service-now.com/cmdb_ci_business_app_list.do?CSV

# Output directory for downloaded files
SERVICENOW_OUTPUT_DIR=./examples

# Run browser in headless mode (set to true for automation)
SERVICENOW_HEADLESS=false

# Browser timeout in milliseconds
SERVICENOW_BROWSER_TIMEOUT=60000

# Download timeout in milliseconds
SERVICENOW_DOWNLOAD_TIMEOUT=120000
"""
