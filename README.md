# scrape-to-sheet

Turn web pages into clean, structured data on a schedule, without writing a new scraper every time. One YAML config describes the source URLs, the row and field selectors, the pagination, and the output columns. The tool fetches, parses, cleans, dedupes, and writes `out/data.csv` (and optionally pushes to a Google Sheet). Point it at a new site by editing a config, not the code.

Built as a reusable, client-ready scraper: the kind of job where someone needs "this catalog / directory / listing in a spreadsheet, refreshed daily."

## The problem

Most scraping jobs are the same five steps wearing different selectors: fetch the page, pick the rows, pull a few fields, clean the mess (whitespace, currency symbols, duplicates), write a spreadsheet. Rewriting that per site is wasteful and brittle. This moves the per-site part into a config file so the engine stays the same and the work becomes "describe the page," not "write Python."

## What it does

- Config-driven: source URL(s), `row_selector`, CSS field selectors (with optional attribute and type), pagination, output columns, dedupe key, all in YAML.
- Two pagination styles: follow a `next` link, or a `url_template` with a page count.
- Cleaning built in: normalize whitespace, parse prices/numbers, drop empty rows, dedupe by a key.
- Output to `out/data.csv`; optional Google Sheets push via `gspread` (documented, not required).
- Runs fully offline against a bundled sample site, so tests and demos are deterministic with no internet.

## Architecture

```mermaid
flowchart LR
    A[configs/*.yaml] --> B[fetch<br/>requests / file://]
    B --> C[parse<br/>BeautifulSoup + CSS]
    C --> D{more pages?}
    D -- next link / template --> B
    D -- done --> E[clean<br/>whitespace, prices,<br/>dedupe, drop empties]
    E --> F[out/data.csv]
    E --> G[(Google Sheet)<br/>optional]
    H[cron / n8n Schedule] -. triggers .-> B
```

## Install

```bash
pipx install git+https://github.com/aminafara123/scrape-to-sheet
scrape-to-sheet configs/books.yaml          # add [sheets] extra for the Google Sheets push
```

For the optional `--sheet` push: `pipx install "git+https://github.com/aminafara123/scrape-to-sheet[sheets]"`.
From a local clone you can also just `pip install .` (or `.[sheets]`).

## Quickstart (clone + make)

```bash
# 1) install
make install            # or: python -m pip install -r requirements.txt

# 2) run the bundled offline example (no internet needed)
make run                # or: python -m scrape_to_sheet configs/books.yaml

# 3) see the result
cat out/data.csv

# 4) run the tests (offline, no API key)
make test               # or: pytest -q
```

## Sample run

Input: `configs/books.yaml` pointed at the bundled `sample_site/` (3 linked pages, one duplicate book across pages).

```
$ python -m scrape_to_sheet configs/books.yaml
Scraped 7 rows -> out/data.csv
```

Output `out/data.csv` (8 raw rows across 3 pages, the duplicate "Cloudwork" deduped to one):

```csv
title,price,rating,availability
The Silent Ledger,51.77,4,In stock (22 available)
Cloudwork,13.99,5,In stock (19 available)
Zero Trust Mornings,1234.56,3,In stock (7 available)
The Pragmatic Scraper,22.5,4,In stock (14 available)
YAML All The Way Down,9.0,2,In stock (3 available)
Config Over Code,33.33,5,In stock (11 available)
Lazy Senior Dev,7.77,5,In stock (99 available)
```

Note the cleaning: `£1,234.56` parsed to `1234.56`, ratings kept as integers, whitespace normalized, the repeated row removed.

## Writing a config

```yaml
name: books
source:
  start_url: ../sample_site/page1.html   # a URL, or a local path relative to this file
pagination:
  next_selector: a.next                   # follow the "next" link...
  max_pages: 10                           # ...up to this many pages (safety cap)
  # or instead:
  # url_template: ../sample_site/page{page}.html
  # pages: 3
row_selector: article.product_pod         # one record per match
fields:
  title:    { selector: h3 a, attr: title }   # read an attribute instead of text
  price:    { selector: p.price_color, type: price }   # type: price | number | int | text
  rating:   { selector: p.star-rating, type: int }
columns: [title, price, rating]           # output order (subset/reorder of fields)
dedupe_key: title                         # drop rows repeating this value
output: out/data.csv
```

The bundled selectors match `books.toscrape.com`, so changing `start_url` to `https://books.toscrape.com/` scrapes the real site with the same config.

## How it works

`load_config` reads the YAML and resolves local paths relative to the config file. `scrape` walks the pages (following `next` links or expanding a URL template), and `parse_page` turns each `row_selector` match into a record using the field selectors. `clean_rows` applies per-field types (`price`/`number`/`int`/`text`), normalizes whitespace, drops empty rows, and dedupes by `dedupe_key`. `write_csv` writes the chosen columns. It is roughly 150 lines in `scrape_to_sheet/core.py`, nothing site-specific.

## Swapping in Playwright (JS-heavy sites)

The default engine is `requests` + BeautifulSoup: lightweight and fast, but it does not run JavaScript. For sites that render content client-side, replace the single `fetch()` function in `scrape_to_sheet/core.py` with a Playwright call:

```python
from playwright.sync_api import sync_playwright

def fetch(url, session=None, timeout=20):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000)
        html = page.content()
        browser.close()
        return html
```

Everything downstream (parse, clean, output) is unchanged. `pip install playwright && playwright install chromium`.

## Google Sheets push (optional)

CSV is always written. To also push to a Google Sheet:

1) `pip install gspread google-auth`
2) Create a Google Cloud service account, enable the Google Sheets API, download its JSON key.
3) Share the target spreadsheet with the service-account email.
4) Set `GOOGLE_APPLICATION_CREDENTIALS=./service-account.json` (see `.env.example`) and add a `sheet:` block to the config with the spreadsheet `id`.
5) Run with `--sheet`:

```bash
python -m scrape_to_sheet configs/books.yaml --sheet
```

If the dependency or credentials are missing, it prints a clear message and still writes the CSV. It never requires an account to run or test.

## Scheduling

Cron (run every day at 07:00, from the project directory):

```cron
0 7 * * *  cd /path/to/scrape-to-sheet && .venv/bin/python -m scrape_to_sheet configs/books.yaml >> out/run.log 2>&1
```

n8n: use a **Schedule Trigger** node, then an **Execute Command** node running the same `python -m scrape_to_sheet ...` line (or a **Code**/HTTP node if you expose it as a service). The Schedule Trigger handles the cadence; this tool handles the scrape.

## Demo

![demo](docs/demo.gif)

See `DEMO.md` for the 60-second recording script.

## Tech stack

Python, `requests`, BeautifulSoup (`beautifulsoup4`), `PyYAML`, `pytest`. Optional: `gspread` + `google-auth` (Sheets), `playwright` (JS rendering).

## License

MIT, (c) 2026 Al Amin Bashir Afara. See `LICENSE`.
