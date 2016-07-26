import pytest
import unittest

from exam import Exam
from lxml import etree, html
from lxml.cssselect import CSSSelector

from toronado import (
    Properties,
    Rule,
    expand_shorthand_box_property,
    from_string,
    inline,
    warn_unsupported_shorthand_property,
)

try:
    from lxml.html import soupparser
except ImportError:
    soupparser = None


class TestCase(Exam, unittest.TestCase):
    pass


def test_expand_shorthand_box_property():
    expand = expand_shorthand_box_property('margin-{}')

    assert expand('1px') == {
        'margin-top': '1px',
        'margin-right': '1px',
        'margin-bottom': '1px',
        'margin-left': '1px',
    }

    assert expand('1px 2px') == {
        'margin-top': '1px',
        'margin-right': '2px',
        'margin-bottom': '1px',
        'margin-left': '2px',
    }

    assert expand('1px 2px 3px') == {
        'margin-top': '1px',
        'margin-right': '2px',
        'margin-bottom': '3px',
        'margin-left': '2px',
    }

    assert expand('1px 2px 3px 4px') == {
        'margin-top': '1px',
        'margin-right': '2px',
        'margin-bottom': '3px',
        'margin-left': '4px',
    }


def test_warn_unsupported_shorthand_property():
    assert warn_unsupported_shorthand_property('font')('10px sans-serif') == {
        'font': '10px sans-serif',
    }


class RuleTestCase(TestCase):
    def test_compares_by_specificity(self):
        self.assertGreater(Rule(0, '#main'), Rule(0, 'div'))
        self.assertEqual(Rule(0, 'div'), Rule(0, 'p'))
        self.assertLess(Rule(0, 'div'), Rule(0, 'div.container'))

    def test_combine_respects_specificity_rules(self):
        properties = Rule.combine((
            Rule(0, 'h1', {
                'font-weight': 'bold',
                'color': 'blue',
            }),
            Rule(0, 'h1#primary', {
                'color': 'red',
            }),
        ))

        self.assertIsInstance(properties, Properties)
        self.assertEqual(properties, {
            'font-weight': 'bold',
            'color': 'red',
        })

    def tests_combine_respects_ordering(self):
        properties = Rule.combine((
            Rule(1, 'h1', {'font-size': '10px', 'font-weight': 'bold'}),
            Rule(2, 'h1', {'font-size': '20px'})
        ))

        self.assertIsInstance(properties, Properties)
        self.assertEqual(properties, {
            'font-weight': 'bold',
            'font-size': '20px',
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

        properties = Properties.from_string('padding: 0 10px')
        self.assertEqual(properties, {
            'padding-top': '0',
            'padding-right': '10px',
            'padding-bottom': '0',
            'padding-left': '10px',
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

    def test_important_styles(self):
        tree = html.document_fromstring("""
            <html>
            <head>
                <style type="text/css">
                    h1 { color: red !important; }
                </style>
            </head>
            <body>
                <h1>Hello, world.</h1>
            </body>
            </html>
        """)

        inline(tree)

        heading = tree.cssselect('h1')[0]
        self.assertEqual(heading.attrib['style'], 'color: red ! important')

    def test_empty_styles(self):
        tree = html.document_fromstring("""
            <html>
            <head>
                <style type="text/css"></style>
            </head>
            <body>
                <h1>Hello, world.</h1>
            </body>
            </html>
        """)

        inline(tree)


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
