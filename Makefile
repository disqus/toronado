develop:
	pip install -e .

test:
	pip install -e .[tests]
	py.test tests.py

.PHONY: develop test
