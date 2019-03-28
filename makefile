SHELL=/bin/bash
version := $(shell sed -rn "s/^VERSION = \"(.*)\"$$/\1/p" setup.py)

clean:
	docker-compose run --rm main find . -type d -name __pycache__ -exec rm -rf {} +

init:
	docker-compose run --rm -u "$$(id -u):$$(id -g)" main bash -c ' \
		set -e; \
		python3.6 -m venv ./.venv; \
		pip install --no-cache-dir --upgrade pip; \
		pip install --no-cache-dir -e .[dev] \
	'

.PHONY: docs
docs:
	docker-compose run --rm -e "VERSION=$(version)" -u "$$(id -u):$$(id -g)" \
		main sphinx-build -b html docs/source docs/build

test:
	docker-compose run --rm main bash -c ' \
		set -e; \
		coverage run -m unittest; \
		coverage report \
	'

coverage-report: test
	docker-compose run --rm -u "$$(id -u):$$(id -g)" main coverage html
