test:
	pip install "file://`pwd`#egg=toronado[tests]" --use-mirrors
	py.test tests.py

.PHONY: test
