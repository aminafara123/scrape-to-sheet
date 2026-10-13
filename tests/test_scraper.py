"""Offline tests: everything runs against the bundled sample_site via file://.
No network, no API key, deterministic."""
from pathlib import Path

from bs4 import BeautifulSoup

from scrape_to_sheet.core import (
    clean_rows,
    load_config,
    parse_page,
    parse_price,
    scrape,
    write_csv,
)

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "sample_site"
BOOKS_CFG = REPO / "configs" / "books.yaml"


def _soup(name):
    return BeautifulSoup((SAMPLE / name).read_text(encoding="utf-8"), "html.parser")


# --- field extraction -------------------------------------------------------
def test_parse_page_extracts_fields():
    cfg, _ = load_config(BOOKS_CFG)
    rows = parse_page(_soup("page1.html"), cfg)
    assert len(rows) == 3
    first = rows[0]
    assert first["title"] == "The Silent Ledger"          # from the title attr
    assert "51.77" in first["price"]                       # raw text, not yet parsed
    assert "22 available" in first["availability"]


# --- pagination traversal + dedupe end to end -------------------------------
def test_scrape_traverses_pages_and_dedupes():
    cfg, base = load_config(BOOKS_CFG)
    rows = scrape(cfg, base)
    # 8 raw rows across 3 pages, one duplicate ("Cloudwork") removed -> 7.
    assert len(rows) == 7
    titles = [r["title"] for r in rows]
    assert titles.count("Cloudwork") == 1
    assert "Lazy Senior Dev" in titles                     # only on the last page


def test_url_template_pagination_mode():
    cfg, base = load_config(BOOKS_CFG)
    cfg["pagination"] = {"url_template": "../sample_site/page{page}.html", "pages": 3}
    cfg.pop("dedupe_key")                                   # keep all rows to count pages
    rows = scrape(cfg, base)
    assert len(rows) == 8                                   # 3 + 3 + 2, no dedupe


# --- price / number parsing -------------------------------------------------
def test_price_parsing():
    assert parse_price("£51.77") == 51.77
    assert parse_price("£1,234.56") == 1234.56             # comma thousands
    assert parse_price("free") is None
    assert parse_price("") is None


def test_type_conversion_applied_in_clean():
    cfg, base = load_config(BOOKS_CFG)
    rows = scrape(cfg, base)
    row = next(r for r in rows if r["title"] == "Zero Trust Mornings")
    assert row["price"] == 1234.56 and isinstance(row["price"], float)
    assert row["rating"] == 3 and isinstance(row["rating"], int)


# --- dedupe + drop-empty on the cleaning step -------------------------------
def test_dedupe_and_drop_empty():
    cfg = {
        "row_selector": "x",
        "fields": {"title": {"selector": "x"}, "price": {"selector": "x", "type": "price"}},
        "dedupe_key": "title",
    }
    raw = [
        {"title": "A", "price": "£1.00"},
        {"title": "A", "price": "£9.99"},   # duplicate key -> dropped
        {"title": "B", "price": "£2.00"},
        {"title": None, "price": None},     # fully empty -> dropped
    ]
    cleaned = clean_rows(raw, cfg)
    assert [r["title"] for r in cleaned] == ["A", "B"]
    assert cleaned[0]["price"] == 1.00


# --- csv output -------------------------------------------------------------
def test_write_csv(tmp_path):
    rows = [{"title": "A", "price": 1.0}, {"title": "B", "price": 2.0}]
    out = write_csv(rows, tmp_path / "data.csv", ["title", "price"])
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "title,price"
    assert "A,1.0" in text
