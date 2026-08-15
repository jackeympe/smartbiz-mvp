.PHONY: help install test run lint format clean

help:
	@echo "SmartBiz MVP commands"
	@echo "  make install  - install deps"
	@echo "  make test     - run pytest"
	@echo "  make run      - start uvicorn"
	@echo "  make lint     - run ruff/mypy if available"
	@echo "  make format   - format code"
	@echo "  make clean    - remove caches"

install:
	uv venv
	uv pip install -e .

test:
	PYTHONPATH='' .venv/Scripts/python.exe -m pytest tests/ -v

run:
	PYTHONPATH='' .venv/Scripts/python.exe -m uvicorn smartbiz.main:app --host 0.0.0.0 --port 8000

lint:
	ruff src/smartbiz/main.py tests/test_main.py || true
	mypy src/smartbiz/main.py || true

format:
	black src/smartbiz/main.py tests/test_main.py || true
	ruff --fix src/smartbiz/main.py tests/test_main.py || true

clean:
	del /s /q src\smartbiz\__pycache__ tests\__pycache__ smartbiz.sqlite || true
