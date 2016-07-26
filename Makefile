lint:
	pip install -e .[dev]
	flake8

test:
	pip install -e .[tests]
	py.test tests.py

.PHONY: lint test
