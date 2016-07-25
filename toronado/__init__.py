from __future__ import absolute_import, unicode_literals, print_function

import itertools
import logging
import sys

from collections import defaultdict
from lxml import html
from lxml.cssselect import CSSSelector
from cssutils import CSSParser
from cssutils.css import (
    CSSRule,
    CSSStyleDeclaration,
    Selector,
)

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    ifilter = filter
else:
    text_type = unicode
    ifilter = __import__('itertools').ifilter


logger = logging.getLogger(__name__)


def expand_shorthand_box_property(name, value):
    bits = value.split()
    size = len(bits)
    if size == 1:
        result = (bits[0],) * 4
    elif size == 2:
        result = (bits[0], bits[1],) * 2
    elif size == 3:
        result = (bits[0], bits[1], bits[2], bits[1])
    elif size == 4:
        result = tuple(bits)
    else:
        raise ValueError('incorrect number of values for box rule: %s' % size)

    sides = ('top', 'right', 'bottom', 'left')
    return {'%s-%s' % (name, side): value for side, value in zip(sides, result)}


def rewrite_margin_property_value(value):
    return expand_box_rule('margin', value)


def rewrite_padding_property_value(value):
    return expand_box_rule('padding', value)


rewrite_map = {
    'margin': expand_shorthand_box_property,
    'padding': expand_shorthand_box_property,
}


def warn_unsupported_shorthand_property(name, value):
    logger.warning(
        "CSS shorthand syntax expansion is not supported for %r. Mixing "
        "shorthand and specific property values (e.g. `font` and `font-size`) "
        "may lead to unexpected results.",
        name,
    )
    return {name: value}


unsupported_shorthand_properties = (
    'animation',
    'background',
    'border',
    'border-bottom',
    'border-color',
    'border-left',
    'border-radius',
    'border-right',
    'border-style',
    'border-top',
    'border-width',
    'font',
    'list-style',
    'transform',
    'transition',
)


for property in unsupported_shorthand_properties:
    rewrite_map[property] = warn_unsupported_shorthand_property


def rewrite_property(property):
    result = rewrite_map.get(
        property.name,
        lambda name, value: {
            name: value,
        }
    )(property.name, property.value)

    if property.priority:
        for key, value in result.items():
            result[key] = "%s ! %s" % (value, property.priority)

    return result


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
        values = {}
        for property in CSSStyleDeclaration(value).getProperties():
            values.update(rewrite_property(property))
        return cls(values)


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
        self.specificity = Selector(selector).specificity

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
    return rule.type == CSSRule.STYLE_RULE


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

    stylesheet_parser = CSSParser(log=logging.getLogger('%s.cssutils' % __name__))

    # Get all stylesheets from the document.
    stylesheets = CSSSelector('style')(tree)
    for stylesheet in stylesheets:
        if stylesheet.attrib.get('inline') == 'false':
            del stylesheet.attrib['inline']
            continue

        if not stylesheet.text:
            continue

        for rule in ifilter(is_style_rule, stylesheet_parser.parseString(stylesheet.text)):
            properties = {}
            for property in rule.style:
                properties.update(rewrite_property(property))

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
