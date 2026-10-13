# Demo script (60 seconds)

Goal: show that one YAML config turns a multi-page site into a clean CSV, offline.

Record a terminal at the project root. Commands and what to say:

1) **Show the config (10s).** Open `configs/books.yaml`.
   Say: "One file describes everything: the start URL, the row selector, the field
   selectors, pagination, and the output columns. No code per site."

2) **Show the sample site (5s).** Open `sample_site/page1.html` in a browser or editor.
   Say: "Three linked pages of fake products, bundled, so this runs with no internet."

3) **Run it (10s).**
   ```bash
   python -m scrape_to_sheet configs/books.yaml
   ```
   Point at the line: `Scraped 7 rows -> out/data.csv`.
   Say: "It followed the next links across all three pages."

4) **Show the output (20s).**
   ```bash
   cat out/data.csv
   ```
   Call out: "£1,234.56 became 1234.56, ratings are integers, whitespace cleaned,
   and the duplicate book across pages was removed. Eight rows in, seven clean rows out."

5) **Run the tests (10s).**
   ```bash
   pytest -q
   ```
   Say: "Seven tests, fully offline, no API key. Parsing, pagination, price parsing,
   dedupe, CSV output. The green bar is the point."

6) **Close (5s).** Scroll the README mermaid diagram and the "swap in Playwright" and
   "Google Sheets" sections. Say: "Same engine for any site, swap in a browser backend
   for JS-heavy pages, push to a Sheet, schedule with cron or n8n."
