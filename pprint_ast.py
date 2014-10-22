#!/usr/bin/env python

import sys
from ast import *

SYMBOLS = {
    # boolean ops
    And:        'and',
    Or:         'or',
    # binary ops
    Add:        '+',
    Sub:        '-',
    Mult:       '*',
    Div:        '/',
    FloorDiv:   '//',
    Mod:        '%',
    LShift:     '<<',
    RShift:     '>>',
    BitOr:      '|',
    BitAnd:     '&',
    BitXor:     '^',
    Pow:        '**',
    # comparision ops
    Eq:         '==',
    Gt:         '>',
    GtE:        '>=',
    In:         'in',
    Is:         'is',
    IsNot:      'is not',
    Lt:         '<',
    LtE:        '<=',
    NotEq:      '!=',
    NotIn:      'not in',
    # unary ops
    Invert:     '~',
    Not:        'not',
    UAdd:       '+',
    USub:       '-'
}



def pprintAst(node, indent='  ', stream=sys.stdout):
    "Pretty-print an AST to the given output stream."
    stream.write(dump2(node))

def dump2(node, level=0, brace=''):
    pfx = ' ' * level + brace
    rv = pfx
    if isinstance(node, AST):
        comma = ''
        close_paren = ')'
        name = node.__class__.__name__ + '('
        print name,
        if type(node) in SYMBOLS:
            name = "'%s'" % SYMBOLS[type(node)]
            close_paren = ''
        print name
        rv += name
        #mult_args = len([b for a, b in iter_fields(node)]) > 1
        single = [b for a, b in iter_fields(node)]
        single = single and not isinstance(single[0], (AST, list))
        for a, b in iter_fields(node):
            rv += comma
            '''
            if mult_args or isinstance(b, list):
                rv += '\n'
            if isinstance(b, (AST, list)) or not mult_args:
                rv += dump2(b, level + 2 + len(brace))
            else:
                rv += ' ' * (level + 2 + len(brace)) + repr(b)
            '''
            if single:
                rv += ' ' * (level + 2 + len(brace)) + repr(b)
            else:
                rv += '\n' + dump2(b, level + 2 + len(brace))
            comma = ','
        return rv + close_paren
    elif isinstance(node, list):
        print node
        if len(node):
            rv += '\n' + dump2(node.pop(0), level, '[')
        else:
            rv += '[]'
        comma = ''
        for x in node:
            rv += comma
            comma = ','
            rv += '\n' + dump2(x, level + 1)
        return rv + ']'
    return repr(node)



f = 'parser_test_source.py'
pprintAst(parse(file(f).read()))

print;print

print dump(parse(file(f).read()), 1, 1)












