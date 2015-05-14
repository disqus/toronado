from __future__ import absolute_import, unicode_literals, print_function

import cssutils
import itertools
import logging
import sys

from collections import defaultdict
from lxml import html
from lxml.cssselect import CSSSelector

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    ifilter = filter
else:
    text_type = unicode
    ifilter = __import__('itertools').ifilter


class Properties(dict):
    """
    A container for CSS properties.
    """
    if PY3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf8')

    def __unicode__(self):
        """
        Renders the properties as a string suitable for inclusion as a HTML tag
        attribute.
        """
        return '; '.join(map(': '.join, self.items()))

    @classmethod
    def from_string(cls, value):
        rules = [
            map(text_type.strip, property.split(':'))
            for property in value.split(';') if property
        ]
        return Properties(rules)


class Rule(object):
    """
    Represents a CSS rule (combination of a CSS selector and style properties.)
    """
    __slots__ = ('selector', 'properties', 'specificity')

    def __init__(self, selector, properties=None):
        self.selector = CSSSelector(selector)
        self.properties = Properties()
        if properties is not None:
            self.properties.update(properties)

        # NOTE: This should be available by `CSSSelector`?
        self.specificity = cssutils.css.Selector(selector).specificity

    def __repr__(self):
        return '<Rule: %s>' % self.selector.css

    def __lt__(self, other):
        return self.specificity < other.specificity

    def __eq__(self, other):
        return self.specificity == other.specificity

    def __hash__(self):
        return hash(self.specificity)

    def update(self, properties):
        """
        Updates this rule, adding the given properties.
        """
        self.properties.update(properties)

    @classmethod
    def combine(cls, rules):
        """
        Combines all of the given rules, following standard specificity rules,
        returning a :class:`Properties` object that contains the correct
        properties for this collection of rules.
        """
        properties = Properties()
        for rule in sorted(rules):
            properties.update(rule.properties)
        return properties


def is_style_rule(rule):
    """
    Returns if a :class:`cssutils.css.CSSRule` is a style rule (not a comment.)
    """
    return rule.type == cssutils.css.CSSRule.STYLE_RULE


def inline(tree):
    """
    Inlines all of the styles within this stylesheet into their matching HTML
    elements. This modifies the original tree in-place, removing all style tags
    and updating the nodes.

    To prevent a ``<style>`` tag from being inlined, add an ``inline="false"``
    attribute::

        <style type="text/css" inline="false">
            /* Any rules contained within this tag will not be inlined. */
        </style>

    """

    def _prio_value(p):
        """
        Format value and priority of a :class:`cssutils.css.Property`.
        """
        if p.priority:
            return "%s ! %s" % (p.value, p.priority)
        return p.value

    rules = {}

    stylesheet_parser = cssutils.CSSParser(log=logging.getLogger('%s.cssutils' % __name__))

    # Get all stylesheets from the document.
    stylesheets = CSSSelector('style')(tree)
    for stylesheet in stylesheets:
        if stylesheet.attrib.get('inline') == 'false':
            del stylesheet.attrib['inline']
            continue

        if not stylesheet.text:
            continue

        for rule in ifilter(is_style_rule, stylesheet_parser.parseString(stylesheet.text)):
            properties = dict([(property.name, _prio_value(property)) for property in rule.style])
            # XXX: This doesn't handle selectors with odd multiple whitespace.
            for selector in map(text_type.strip, rule.selectorText.split(',')):
                rule = rules.get(selector, None)
                if rule is None:
                    rule = rules[selector] = Rule(selector)
                rule.update(properties)

        stylesheet.getparent().remove(stylesheet)

    # Collect all nodes matching our style rules.
    nodes = defaultdict(list)
    for rule in rules.values():
        for node in rule.selector(tree):
            nodes[node].append(rule)

    # Apply all styles to our collected elements.
    for node, rules in nodes.items():
        properties = Rule.combine(rules)

        # If this node already has a style attribute, we need to apply those
        # styles on top of the CSS rules from the stylesheet.
        style_attr = node.attrib.get('style')
        if style_attr is not None:
            properties.update(Properties.from_string(style_attr))

        node.attrib['style'] = '%s' % properties


def from_string(string):
    tree = html.document_fromstring(string)
    inline(tree)
    return html.tostring(tree)
