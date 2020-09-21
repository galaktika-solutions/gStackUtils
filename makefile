SHELL=/bin/bash

init:
	python3 -m venv ./.venv; \
	./.venv/bin/pip install --no-cache-dir --upgrade pip; \
	./.venv/bin/pip install --no-cache-dir -e .[dev] \

test:
		coverage run -m unittest; \
		coverage report
