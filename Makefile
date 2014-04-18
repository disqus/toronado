test:
	pip install --use-mirrors -e .[tests]
	py.test tests.py

.PHONY: test
