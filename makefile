SHELL=/bin/bash

init:
	python3 -m venv ./.venv; \
	./.venv/bin/pip install --no-cache-dir --upgrade pip; \
	./.venv/bin/pip install --no-cache-dir -e .[dev] \

test:
		coverage run -m unittest; \
		coverage report

distribute:
	rm -rf dist
	python setup.py sdist
	TWINE_USERNAME="$$(gstack conf retrieve username)" TWINE_PASSWORD="$$(gstack conf retrieve password)" twine upload dist/*
