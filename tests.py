import unittest2
from exam import Exam, fixture
from lxml import html

from toronado import Rule, Properties, inline


class TestCase(Exam, unittest2.TestCase):
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

        self.assertIn(u'%s' % properties, expected)

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
