import io
import sys

import pandas as pd

from data import fetch_html

# Usage:  python3 inspect_page.py "https://fbref.com/..."
# Opens the page once and prints every table on it, so we can see which one
# we need (and what its columns are called) BEFORE writing code that uses it.
if len(sys.argv) != 2:
    sys.exit('Usage: python3 inspect_page.py "<page url>"')

html = fetch_html(sys.argv[1])
tables = pd.read_html(io.StringIO(html))

print(f"\nFound {len(tables)} tables on this page.\n")
for i, table in enumerate(tables):
    # Two-row headers come as pairs like ('Standard', 'Sh'); show the last part.
    columns = [col[-1] if isinstance(col, tuple) else col for col in table.columns]
    print(f"Table {i}: {table.shape[0]} rows x {table.shape[1]} columns")
    print(f"   columns: {columns}\n")