"""
Data transformer for converting ServiceNow export to expected CSV format.

This module handles mapping ServiceNow field names to the expected format
for the Draw.io Application Landscape generator.
"""
import csv
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config import config


class DataTransformer:
    """Transform ServiceNow data to the expected CSV format."""

    def __init__(self, column_mappings: Optional[dict] = None):
        """
        Initialize the transformer.

        Args:
            column_mappings: Dict mapping ServiceNow column names to output column names.
                           If None, uses default mappings from config.
        """
        self.column_mappings = column_mappings or config.column_mappings

    def transform_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        output_type: str = 'applications'
    ) -> Path:
        """
        Transform a ServiceNow export file to the expected format.

        Args:
            input_path: Path to the input CSV file
            output_path: Path for the output file (default: auto-generated)
            output_type: 'applications' or 'capabilities'

        Returns:
            Path to the transformed file
        """
        input_path = Path(input_path)

        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = input_path.parent / f"{output_type}_{timestamp}.csv"
        else:
            output_path = Path(output_path)

        # Read input file
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            # Handle potential BOM and different delimiters
            content = f.read()
            dialect = self._detect_dialect(content)
            f.seek(0)
            reader = csv.DictReader(f, dialect=dialect)
            input_rows = list(reader)

        if not input_rows:
            raise ValueError(f"No data found in {input_path}")

        # Detect and create mapping
        input_columns = list(input_rows[0].keys())
        column_map = self._create_column_map(input_columns)

        print(f"Detected column mappings:")
        for src, dst in column_map.items():
            print(f"  {src} -> {dst}")

        # Determine output columns based on type
        if output_type == 'applications':
            output_columns = [
                'Level1', 'Level2', 'AppName', 'TC', 'StatusRAG', 'Resilience',
                'HostingPercent', 'HostingPattern1', 'HostingPattern2',
                'Arrow1', 'Arrow2', 'Link', 'Controls', 'DecommDate'
            ]
        else:  # capabilities
            output_columns = [
                'Level1', 'Level2', 'AppName', 'TC', 'StatusRAG',
                'Category', 'Link', 'Date'
            ]

        # Transform rows
        transformed_rows = []
        for row in input_rows:
            transformed_row = self._transform_row(row, column_map, output_columns)
            if transformed_row:
                transformed_rows.append(transformed_row)

        # Write output
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_columns)
            writer.writeheader()
            writer.writerows(transformed_rows)

        print(f"\nTransformed {len(transformed_rows)} rows")
        print(f"Output saved to: {output_path}")

        return output_path

    def _detect_dialect(self, content: str) -> csv.Dialect:
        """Detect CSV dialect from content."""
        try:
            sample = content[:4096]
            sniffer = csv.Sniffer()
            return sniffer.sniff(sample)
        except:
            return csv.excel  # Default to standard CSV

    def _create_column_map(self, input_columns: list[str]) -> dict:
        """
        Create a mapping from input columns to output columns.

        Uses configured mappings and fuzzy matching for common patterns.
        """
        column_map = {}

        # Normalize input column names for matching
        normalized_inputs = {self._normalize_name(col): col for col in input_columns}

        # First pass: exact matches from config
        for snow_col, output_col in self.column_mappings.items():
            normalized = self._normalize_name(snow_col)
            if normalized in normalized_inputs:
                column_map[normalized_inputs[normalized]] = output_col

        # Second pass: fuzzy matching for unmapped columns
        common_patterns = {
            # Level/Capability patterns
            r'(capability|domain|level).*(l1|level.?1|parent)': 'Level1',
            r'(capability|domain|level).*(l2|level.?2|child)': 'Level2',
            r'l1.*(capability|domain)': 'Level1',
            r'l2.*(capability|domain)': 'Level2',

            # Application name patterns
            r'^name$': 'AppName',
            r'app.*name': 'AppName',
            r'application.*(name|title)': 'AppName',
            r'display.*name': 'AppName',

            # Code/ID patterns
            r'(tech|technical).*(code|id)': 'TC',
            r'^(code|id)$': 'TC',
            r'app.*(code|id)': 'TC',

            # Status patterns
            r'(status|rag|health)': 'StatusRAG',
            r'traffic.*light': 'StatusRAG',

            # Resilience patterns
            r'resilien': 'Resilience',
            r'tier': 'Resilience',
            r'criticality': 'Resilience',

            # Hosting patterns
            r'cloud.*(%|percent|pct)': 'HostingPercent',
            r'hosting.*pattern.*1': 'HostingPattern1',
            r'hosting.*pattern.*2': 'HostingPattern2',
            r'primary.*(host|platform)': 'HostingPattern1',
            r'secondary.*(host|platform)': 'HostingPattern2',

            # Arrow/flow patterns
            r'(data.*flow|arrow|direction).*1': 'Arrow1',
            r'(data.*flow|arrow|direction).*2': 'Arrow2',
            r'(inbound|in).*flow': 'Arrow1',
            r'(outbound|out).*flow': 'Arrow2',

            # Link patterns
            r'^link$': 'Link',
            r'url(?!.*control)': 'Link',
            r'control.*link': 'Controls',
            r'control.*url': 'Controls',

            # Date patterns
            r'decom': 'DecommDate',
            r'retire': 'DecommDate',
            r'end.*(date|of.*life)': 'DecommDate',

            # Category patterns
            r'category': 'Category',
            r'type': 'Category',
        }

        for col in input_columns:
            if col in column_map:
                continue

            normalized = self._normalize_name(col)
            for pattern, output_col in common_patterns.items():
                if re.search(pattern, normalized, re.IGNORECASE):
                    if output_col not in column_map.values():
                        column_map[col] = output_col
                        break

        return column_map

    def _normalize_name(self, name: str) -> str:
        """Normalize a column name for matching."""
        # Remove common prefixes
        name = re.sub(r'^u_', '', name)  # ServiceNow custom field prefix
        name = re.sub(r'^cmdb_', '', name)
        # Convert to lowercase, replace separators with underscores
        name = name.lower()
        name = re.sub(r'[\s\-\.]+', '_', name)
        return name

    def _transform_row(
        self,
        row: dict,
        column_map: dict,
        output_columns: list[str]
    ) -> Optional[dict]:
        """Transform a single row."""
        output_row = {}

        for output_col in output_columns:
            # Find the input column that maps to this output column
            value = ''
            for input_col, mapped_col in column_map.items():
                if mapped_col == output_col:
                    value = row.get(input_col, '')
                    break

            # Apply transformations based on column type
            value = self._transform_value(output_col, value)
            output_row[output_col] = value

        # Skip rows without required fields
        if not output_row.get('AppName') and not output_row.get('Level1'):
            return None

        return output_row

    def _transform_value(self, column: str, value: str) -> str:
        """Apply column-specific transformations."""
        if value is None:
            return ''

        value = str(value).strip()

        if column == 'StatusRAG':
            # Normalize RAG status values
            value_lower = value.lower()
            if value_lower in ['green', 'g', '1', 'good', 'ok', 'healthy']:
                return 'green'
            elif value_lower in ['amber', 'yellow', 'a', 'y', '2', 'warning', 'caution']:
                return 'amber'
            elif value_lower in ['red', 'r', '3', 'bad', 'critical', 'unhealthy']:
                return 'red'
            return value

        elif column == 'Resilience':
            # Normalize resilience tier to number
            try:
                num = int(re.search(r'\d+', value).group())
                return str(min(max(num, 0), 4))  # Clamp to 0-4
            except:
                return value

        elif column == 'HostingPercent':
            # Normalize percentage
            try:
                num = int(re.search(r'\d+', value).group())
                return str(min(max(num, 0), 100))  # Clamp to 0-100
            except:
                return value

        elif column in ['Arrow1', 'Arrow2']:
            # Normalize arrow direction
            value_lower = value.lower()
            if value_lower in ['up', 'in', 'inbound', 'yes', '1', 'true']:
                return 'up'
            elif value_lower in ['down', 'out', 'outbound', 'no', '0', 'false']:
                return 'down'
            return value

        elif column == 'DecommDate':
            # Try to parse and normalize date
            return self._normalize_date(value)

        return value

    def _normalize_date(self, value: str) -> str:
        """Normalize date to YYYY-MM format."""
        if not value:
            return ''

        # Common date formats to try
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%m/%d/%Y',
            '%Y-%m',
            '%Y/%m',
            '%d/%m/%y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return dt.strftime('%Y-%m')
            except ValueError:
                continue

        # If no format matches, return original
        return value


def transform_export(
    input_path: str,
    output_path: Optional[str] = None,
    output_type: str = 'applications'
) -> Path:
    """
    Convenience function to transform a ServiceNow export.

    Args:
        input_path: Path to input CSV file
        output_path: Path for output file (optional)
        output_type: 'applications' or 'capabilities'

    Returns:
        Path to the transformed file
    """
    transformer = DataTransformer()
    return transformer.transform_file(
        Path(input_path),
        Path(output_path) if output_path else None,
        output_type
    )
