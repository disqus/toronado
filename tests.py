import pytest
import sys
import unittest

from exam import Exam, fixture
from lxml import etree, html
from lxml.cssselect import CSSSelector

from toronado import Rule, Properties, inline, from_string

try:
    from lxml.html import soupparser
except ImportError:
    soupparser = None


class TestCase(Exam, unittest.TestCase):
    pass


class RuleTestCase(TestCase):
    def test_compares_by_specificity(self):
        self.assertGreater(Rule('#main'), Rule('div'))
        self.assertEqual(Rule('div'), Rule('p'))
        self.assertLess(Rule('div'), Rule('div.container'))

    def test_combine_respects_specificity_rules(self):
        properties = Rule.combine((
            Rule('h1', {
                'font-weight': 'bold',
                'color': 'blue',
            }),
            Rule('h1#primary', {
                'color': 'red',
            }),
        ))

        self.assertIsInstance(properties, Properties)
        self.assertEqual(properties, {
            'font-weight': 'bold',
            'color': 'red',
        })


class PropertiesTestCase(TestCase):
    def test_serializes_to_attribute_string(self):
        properties = Properties({
            'font-weight': 'bold',
            'color': 'red',
        })

        # XXX: Ordering is non-deterministic, so we have to check both variations.
        expected = set((
            'font-weight: bold; color: red',
            'color: red; font-weight: bold',
        ))

        self.assertIn('%s' % (properties,), expected)

    def test_from_string(self):
        properties = Properties.from_string('color: red; font-weight: bold')
        self.assertEqual(properties, {
            'color': 'red',
            'font-weight': 'bold',
        })

    def test_from_string_cleans_whitespace(self):
        properties = Properties.from_string('color : red;\nfont-weight: bold ;')
        self.assertEqual(properties, {
            'color': 'red',
            'font-weight': 'bold',
        })


class InlineTestCase(TestCase):
    def test_inlines_styles(self):
        tree = html.document_fromstring("""
            <html>
            <head>
                <style type="text/css">
                    h1 { color: red; }
                </style>
            </head>
            <body>
                <h1>Hello, world.</h1>
            </body>
            </html>
        """)

        inline(tree)

        heading, = tree.cssselect('h1')
        self.assertEqual(heading.attrib['style'], 'color: red')

    def test_does_not_override_inlined_styles(self):
        tree = html.document_fromstring("""
            <html>
            <head>
                <style type="text/css">
                    h1 {
                        color: red;
                        display: block;
                    }
                </style>
            </head>
            <body>
                <h1 style="color: blue; font-weight: bold">Hello, world.</h1>
            </body>
            </html>
        """)

        inline(tree)

        heading, = tree.cssselect('h1')
        properties = Properties.from_string(heading.attrib['style'])
        self.assertEqual(properties, {
            'color': 'blue',
            'display': 'block',
            'font-weight': 'bold',
        })

    def test_removes_compiled_styles(self):
        tree = html.document_fromstring("""
            <html>
            <head>
                <style type="text/css">
                    h1 { font-weight: bold; }
                </style>
            </head>
            <body>
                <h1>Hello, world.</h1>
            </body>
            </html>
        """)

        inline(tree)

        heading, = tree.cssselect('h1')
        self.assertEqual(heading.attrib['style'], 'font-weight: bold')

        self.assertEqual(len(tree.cssselect('style')), 0)

    def test_skips_inline_false(self):
        tree = html.document_fromstring("""
            <html>
            <head>
                <style type="text/css">
                    h1 { font-weight: bold; }
                </style>
                <style type="text/css" inline="false">
                    h1 { color: red; }
                </style>
            </head>
            <body>
                <h1>Hello, world.</h1>
            </body>
            </html>
        """)

        inline(tree)

        heading, = tree.cssselect('h1')
        self.assertEqual(heading.attrib['style'], 'font-weight: bold')

        stylesheet, = tree.cssselect('style')
        self.assertNotIn('inline', stylesheet.attrib)


class ParserTestCase(TestCase):
    document = """
        <html>
        <head>
            <style type="text/css">
                h1 { color: red; }
            </style>
        </head>
        <body>
            <h1>Hello, world.</h1>
        </body>
        </html>
    """

    def assertInlines(self, tree):
        inline(tree)

        heading, = CSSSelector('h1')(tree)
        self.assertEqual(heading.attrib['style'], 'color: red')

    def test_etree(self):
        tree = etree.fromstring(self.document)
        self.assertInlines(tree)

    def test_html(self):
        tree = html.document_fromstring(self.document)
        self.assertInlines(tree)

    @pytest.mark.skipif(soupparser is None,
                        reason='BeautifulSoup is not installed')
    def test_beautifulsoup(self):
        tree = soupparser.fromstring(self.document)
        self.assertInlines(tree)

    def test_from_string(self):
        result = from_string(self.document)
        tree = etree.fromstring(result)
        self.assertInlines(tree)
