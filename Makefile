.PHONY: install test run clean

install:
	python -m pip install -r requirements.txt

test:
	pytest -q

run:
	python -m scrape_to_sheet configs/books.yaml

clean:
	rm -rf out __pycache__ */__pycache__ .pytest_cache
