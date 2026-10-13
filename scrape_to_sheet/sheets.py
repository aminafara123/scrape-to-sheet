"""Optional Google Sheets push via gspread + a service account.

This is NOT required to run or test the scraper. CSV is always written.
Setup (one time):
  1) Create a Google Cloud service account, enable the Google Sheets API,
     download its JSON key.
  2) Share the target spreadsheet with the service-account email.
  3) pip install gspread google-auth
  4) Set env / config: GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
     and a config block:
         sheet:
           id: "<spreadsheet-id>"        # from the sheet URL
           worksheet: "Sheet1"           # optional, defaults to first
Then run:  python -m scrape_to_sheet configs/books.yaml --sheet
"""
from __future__ import annotations

import os


def push_to_sheet(rows, columns, sheet_cfg):
    """Overwrite a worksheet with header + rows. Returns rows written.

    Fails with a clear message (not a crash) if deps or credentials are missing.
    """
    sheet_cfg = sheet_cfg or {}
    sheet_id = sheet_cfg.get("id") or os.environ.get("SHEET_ID")
    if not sheet_id:
        raise SystemExit("No sheet id: set config 'sheet.id' or env SHEET_ID.")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise SystemExit("Google Sheets push needs: pip install gspread google-auth")

    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path or not os.path.exists(key_path):
        raise SystemExit(
            "Set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON file "
            "(see scrape_to_sheet/sheets.py for setup)."
        )

    creds = Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    ws_name = sheet_cfg.get("worksheet")
    ws = spreadsheet.worksheet(ws_name) if ws_name else spreadsheet.sheet1

    values = [columns] + [["" if r.get(c) is None else r.get(c) for c in columns] for r in rows]
    ws.clear()
    ws.update(values, "A1")
    return len(rows)
