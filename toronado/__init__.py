import itertools
import logging
import string
from collections import defaultdict

import cssutils
from lxml.cssselect import CSSSelector


class Properties(dict):
    """
    A container for CSS properties.
    """
    def __unicode__(self):
        """
        Renders the properties as a string suitable for inclusion as a HTML tag
        attribute.
        """
        return '; '.join(map(': '.join, self.items()))

    @classmethod
    def from_string(cls, value):
        rules = [map(string.strip, property.split(':')) for property in value.split(';') if property]
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

    def __cmp__(self, other):
        """
        Compares two rules by specificity.
        """
        return cmp(self.specificity, other.specificity)

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
    rules = {}

    stylesheet_parser = cssutils.CSSParser(log=logging.getLogger('%s.cssutils' % __name__))

    # Get all stylesheets from the document.
    stylesheets = CSSSelector('style')(tree)
    for stylesheet in stylesheets:
        if stylesheet.attrib.get('inline') == 'false':
            del stylesheet.attrib['inline']
            continue

        for rule in itertools.ifilter(is_style_rule, stylesheet_parser.parseString(stylesheet.text)):
            properties = dict([(property.name, property.value) for property in rule.style])
            # XXX: This doesn't handle selectors with odd multiple whitespace.
            for selector in map(string.strip, rule.selectorText.split(',')):
                rule = rules.get(selector, None)
                if rule is None:
                    rule = rules[selector] = Rule(selector)
                rule.update(properties)

        stylesheet.getparent().remove(stylesheet)

    # Collect all nodes matching our style rules.
    nodes = defaultdict(list)
    for rule in rules.itervalues():
        for node in rule.selector(tree):
            nodes[node].append(rule)

    # Apply all styles to our collected elements.
    for node, rules in nodes.iteritems():
        properties = Rule.combine(rules)

        # If this node already has a style attribute, we need to apply those
        # styles on top of the CSS rules from the stylesheet.
        style_attr = node.attrib.get('style')
        if style_attr is not None:
            properties.update(Properties.from_string(style_attr))

        node.attrib['style'] = u'%s' % properties
