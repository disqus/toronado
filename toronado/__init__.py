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
    text_type = unicode  # flake8: noqa
    ifilter = __import__('itertools').ifilter


logger = logging.getLogger(__name__)


def expand_box_property_names(template):
    return list(map(template.format, ('top', 'right', 'bottom', 'left')))


def expand_shorthand_box_property(template):
    names = expand_box_property_names(template)

    def expand_property(value):
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

        return dict(zip(names, result))

    return expand_property


def warn_unsupported_shorthand_property(property):
    def expand_property(value):
        logger.warning(
            "CSS shorthand syntax expansion is not supported for %r. Mixing "
            "shorthand and specific property values (e.g. `font` and `font-size`) "
            "may lead to unexpected results.",
            property,
        )
        return {property: value}

    return expand_property


def compress_box_property(shorthand, template):
    names = expand_box_property_names(template)

    def compress_property(value):
        if not set(value).issuperset(set(names)):
            return value

        top, right, bottom, left = map(value.pop, names)

        if top == right == bottom == left:
            value[shorthand] = top
        elif top == bottom and right == left:
            value[shorthand] = '{} {}'.format(top, right)
        elif right == left:
            value[shorthand] = '{} {} {}'.format(top, right, bottom)
        else:
            value[shorthand] = '{} {} {} {}'.format(top, right, bottom, left)

        return value

    return compress_property


shorthand_box_properties = {
    'margin': 'margin-{}',
    'padding': 'padding-{}',
    'border-width': 'border-{}-width',
}

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
    'font',
    'list-style',
    'transform',
    'transition',
)


expansion_rewrite_map = {}
property_processors = []

for property, template in shorthand_box_properties.items():
    expansion_rewrite_map[property] = expand_shorthand_box_property(template)
    property_processors.append(compress_box_property(property, template))

for property in unsupported_shorthand_properties:
    expansion_rewrite_map[property] = warn_unsupported_shorthand_property(property)


def expand_property(property):
    result = expansion_rewrite_map.get(
        property.name,
        lambda value: {
            property.name: value,
        }
    )(property.value)

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
        value = self.copy()
        for processor in property_processors:
            value = processor(value)

        return '; '.join(map(': '.join, value.items()))

    @classmethod
    def from_string(cls, value):
        values = {}
        for property in CSSStyleDeclaration(value).getProperties():
            values.update(expand_property(property))
        return cls(values)


class Rule(object):
    """
    Represents a CSS rule (combination of a CSS selector and style properties.)
    """
    __slots__ = ('id', 'selector', 'properties', 'specificity')

    def __init__(self, id, selector, properties=None):
        self.id = id
        self.selector = CSSSelector(selector)
        self.properties = Properties()
        if properties is not None:
            self.properties.update(properties)

        # NOTE: This should be available by `CSSSelector`?
        self.specificity = Selector(selector).specificity

    def __repr__(self):
        return '<Rule: %s>' % self.selector.css

    def __lt__(self, other):
        return (self.specificity, self.id) < (other.specificity, other.id)

    def __eq__(self, other):
        return (self.specificity, self.id) == (other.specificity, other.id)

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
    rules = defaultdict(list)
    rule_id_sequence = itertools.count()

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
                properties.update(expand_property(property))

            # XXX: This doesn't handle selectors with odd multiple whitespace.
            for selector in map(text_type.strip, rule.selectorText.split(',')):
                rule = Rule(
                    next(rule_id_sequence),
                    selector,
                    properties,
                )
                rules[rule.selector].append(rule)

        stylesheet.getparent().remove(stylesheet)

    # Collect all nodes matching our style rules.
    nodes = defaultdict(list)
    for selector, rs in rules.items():
        for node in selector(tree):
            nodes[node].extend(rs)

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
