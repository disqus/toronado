toronado
========

Fast lxml-based CSS stylesheet inliner.

Usage
~~~~~

.. code::

    >>> from lxml import html
    >>> from toronado import inline
    >>> document = """<html>
    ... <head>
    ...     <style type="text/css">
    ...         h1 { color: red; }
    ...     </style>
    ... </head>
    ... <body><h1>Hello, world.</h1></body>
    ... </html>"""
    >>> tree = html.document_fromstring(document)
    >>> inline(tree)
    >>> print html.tostring(tree)
    <html><head></head><body><h1 style="color: red">Hello, world.</h1></body></html>
