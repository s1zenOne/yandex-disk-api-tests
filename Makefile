.PHONY: install test unit integration lint

install:
	python -m pip install -r requirements.txt

test:
	pytest

unit:
	pytest -m "not integration"

integration:
	pytest -m integration

lint:
	ruff check .

