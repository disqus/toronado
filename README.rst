toronado
========

Fast lxml-based CSS stylesheet inliner.

.. image:: https://travis-ci.org/disqus/toronado.svg?branch=master
    :target: https://travis-ci.org/disqus/toronado

Tested against Python 2.7, 3.3, 3.4, and 3.5.

Installation
~~~~~~~~~~~~

This package is hosted on `PyPI <https://pypi.python.org/pypi/toronado>`_ and
can be installed using ``pip`` or ``easy_install``::

    pip install toronado

Usage
~~~~~

.. code:: python

    >>> import toronado
    >>> document = """<html>
    ... <head>
    ...     <style type="text/css">
    ...         h1 { color: red; }
    ...     </style>
    ... </head>
    ... <body><h1>Hello, world.</h1></body>
    ... </html>"""
    >>> print(toronado.from_string(document))
    <html><head></head><body><h1 style="color: red">Hello, world.</h1></body></html>

Command Line Usage
------------------

To inline a file directly from the command line, you can use the following::

    python -m toronado input.html

The inlined HTML will be printed to your shell's ``stdout`` stream, and can
also be redirected to a file::

    python -m toronado input.html > output.html

Known Issues
------------

* Expansion of some shorthand properties is not fully implemented (`margin` and
  `padding` are supported, however.) Mixing shorthand properties and specific
  properties such as `font` and `font-size` may lead to unexpected inheritance
  results. (See GH-19 for details.)
