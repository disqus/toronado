test:
	pip install -e .[tests]
	py.test tests.py

.PHONY: test
