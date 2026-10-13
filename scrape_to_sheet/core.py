"""Config-driven scraper: YAML in, clean rows out.

Flow: load_config -> scrape (fetch + parse + paginate) -> clean_rows -> write_csv.
No site-specific code lives here; a YAML config describes everything.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

UA = "scrape-to-sheet/1.0 (+https://github.com/aminafara123/scrape-to-sheet)"
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+")


# --- cleaning helpers -------------------------------------------------------
def normalize_ws(s):
    """Collapse all runs of whitespace to a single space and strip."""
    return re.sub(r"\s+", " ", s).strip() if s else ""


def parse_number(s):
    """First number in a string -> float. '£1,234.56' -> 1234.56, '' -> None."""
    if s is None:
        return None
    m = _NUM_RE.search(str(s).replace(",", ""))
    return float(m.group()) if m else None


def parse_price(s):
    v = parse_number(s)
    return round(v, 2) if v is not None else None


def _convert(value, typ):
    if typ == "price":
        return parse_price(value)
    if typ in ("number", "float"):
        return parse_number(value)
    if typ == "int":
        v = parse_number(value)
        return int(v) if v is not None else None
    return normalize_ws(value) if value is not None else None


# --- config -----------------------------------------------------------------
def load_config(path):
    """Read a YAML config and return (config_dict, base_dir).

    base_dir is the config's own folder; relative local source paths resolve
    against it, so a config runs the same from any working directory.
    """
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("row_selector", "fields"):
        if key not in cfg:
            raise ValueError(f"config missing required key: {key!r}")
    pag = cfg.get("pagination", {}) or {}
    if "source" not in cfg and "url_template" not in pag:
        raise ValueError("config needs 'source.start_url' or 'pagination.url_template'")
    return cfg, path.parent


def _resolve(path_or_url, base_dir):
    """Turn a config location into a fetchable URL.

    http(s) URLs pass through; anything else is treated as a local path
    (absolute, or relative to base_dir) and returned as a file:// URL.
    """
    if "://" in path_or_url:
        return path_or_url
    return (base_dir / path_or_url).resolve().as_uri()


# --- fetch + parse ----------------------------------------------------------
def fetch(url, session=None, timeout=20):
    """Return page text for an http(s) URL or a local file:// URL.

    file:// is handled directly (no server) so bundled sample sites and tests
    run with zero network. Swap this one function for a Playwright backend to
    render JS-heavy pages (see README).
    """
    if url.startswith("file://"):
        return Path(unquote(urlparse(url).path)).read_text(encoding="utf-8")
    sess = session or requests
    resp = sess.get(url, timeout=timeout, headers={"User-Agent": UA})
    resp.raise_for_status()
    return resp.text


def _extract_field(row, spec):
    spec = spec or {}
    el = row.select_one(spec["selector"])
    if el is None:
        return None
    attr = spec.get("attr")
    return el.get(attr) if attr else el.get_text()


def parse_page(soup, config):
    """Extract one record per row element from an already-parsed page."""
    rows = []
    for row in soup.select(config["row_selector"]):
        rows.append({name: _extract_field(row, spec) for name, spec in config["fields"].items()})
    return rows


def _page_urls(config, base_dir):
    """Yield URLs for url_template pagination (page N over a count)."""
    pag = config["pagination"]
    start = pag.get("start", 1)
    for page in range(start, start + pag.get("pages", 1)):
        yield _resolve(pag["url_template"].format(page=page), base_dir)


def scrape(config, base_dir, session=None):
    """Run the whole pipeline and return cleaned rows."""
    pag = config.get("pagination", {}) or {}
    raw = []
    if pag.get("url_template"):
        for url in _page_urls(config, base_dir):
            raw += parse_page(BeautifulSoup(fetch(url, session), "html.parser"), config)
    else:
        url = _resolve(config["source"]["start_url"], base_dir)
        max_pages = pag.get("max_pages", pag.get("pages", 1))
        selector = pag.get("next_selector")
        seen = 0
        while url and seen < max_pages:
            soup = BeautifulSoup(fetch(url, session), "html.parser")
            raw += parse_page(soup, config)
            seen += 1
            nxt = soup.select_one(selector) if selector else None
            url = urljoin(url, nxt["href"]) if (nxt and nxt.get("href")) else None
    return clean_rows(raw, config)


def clean_rows(rows, config):
    """Type-convert, normalize whitespace, drop empty rows, dedupe by key."""
    fields = config["fields"]
    columns = config.get("columns") or list(fields)
    key = config.get("dedupe_key")
    seen, out = set(), []
    for row in rows:
        rec = {name: _convert(row.get(name), (spec or {}).get("type", "text"))
               for name, spec in fields.items()}
        if not any(v not in (None, "") for v in rec.values()):
            continue  # drop fully-empty rows
        if key:
            k = rec.get(key)
            if k in seen:
                continue
            seen.add(k)
        out.append({c: rec.get(c) for c in columns})
    return out


# --- output -----------------------------------------------------------------
def write_csv(rows, path, columns):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


# --- CLI --------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Config-driven web scraper -> CSV / Google Sheet.")
    ap.add_argument("config", help="path to a YAML config (e.g. configs/books.yaml)")
    ap.add_argument("--out", help="output CSV path (default: config 'output' or out/data.csv)")
    ap.add_argument("--sheet", action="store_true", help="also push to Google Sheets (needs setup)")
    args = ap.parse_args(argv)

    config, base_dir = load_config(args.config)
    rows = scrape(config, base_dir)
    columns = config.get("columns") or list(config["fields"])
    out = args.out or config.get("output", "out/data.csv")
    write_csv(rows, out, columns)
    print(f"Scraped {len(rows)} rows -> {out}")

    if args.sheet or config.get("sheet"):
        from .sheets import push_to_sheet
        n = push_to_sheet(rows, columns, config.get("sheet", {}))
        print(f"Pushed {n} rows to Google Sheet")


if __name__ == "__main__":
    main()
