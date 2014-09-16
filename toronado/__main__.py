from optparse import OptionParser

import lxml.html

import toronado


parser = OptionParser(usage='usage: %prog infile')
try:
    (options, (infile,)) = parser.parse_args()
except ValueError:
    parser.print_usage()
    raise SystemExit(1)

tree = lxml.html.parse(open(infile, 'r'))
toronado.inline(tree)
print(lxml.html.tostring(tree, pretty_print=True))
