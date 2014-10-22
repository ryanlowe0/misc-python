#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from ast import *
from tokenize import generate_tokens, COMMENT, NL, NEWLINE

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





class CodeParser(object):
    '''Create Code object from Python Tokens and AST Nodes.'''

    def __init__(self, source_file):
        self.ast = parse(file(source_file).read())
        self.tokens = [[]]  # organize by lines to aid matching with ast nodes
        for t in generate_tokens(file(source_file).readline):
            if t[0] in (NL, NEWLINE):
                self.tokens.append([])
            else:
                self.tokens[-1].append(t)
        self.visit(self.ast)

    def getToken(self, tok, start=0):
        for line in self.tokens[start:]:
            for t in line:
                if t[1] == tok:
                    return t

    # Base Visitor
    
    def visit(self, node, *args, **kw):
        method = 'none'
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kw)

    def generic_visit(self, node, *args, **kw):
        '''Called if no explicit visitor function exists for a node.'''
        raise NotImplementedError('visit_%s not defined' %
                                  node.__class__.__name__)

    def write(self, s):
        indentation = self.indent * self.indent_level
        if len(self.code) < self.lineno:
            self.code += [''] * (self.lineno - len(self.code))
            self.new_lines = 0
        if not self.code[self.lineno - 1]:
            self.code[self.lineno - 1] += indentation
        # expecting empty new line, but statement already there:
        # must be ;-separated statements
        if self.new_lines and self.code[self.lineno - 1].strip():
            self.code[self.lineno - 1] += ';'
            self.new_lines = 0
        self.code[self.lineno - 1] += s

    # Extracted visit patterns

    def body(self, statements):
        self.indent_level += 1
        for stmt in statements:
            self.visit(stmt)
        self.indent_level -= 1

    def body_else(self, node):
        self.body(node.body)
        if node.orelse:
            self.newline()
            self.lineno = self.getLineNo('else', self.lineno)
            self.write('else:')
            self.body(node.orelse)

    def decorators(self, node):
        first = True
        for decorator in node.decorator_list:
            # newline not needed for 1st because funcdef already adds 2
            if not first: self.newline(decorator)
            first = False
            self.write('@')
            self.visit(decorator)

    def generator(self, node, wrapper):
        # wrapper = [], (), or {}
        self.write(wrapper[0])
        self.visit(node.elt)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.write(wrapper[1])

    def sequence(self, node, wrapper):
        self.write(wrapper[0])
        comma = ''
        for item in node.elts:
            self.write(comma)
            comma = ', '
            self.visit(item)
        self.write(wrapper[1])

    def signature(self, node):
        padding = [None] * (len(node.args) - len(node.defaults))
        comma = ''
        for arg, default in zip(node.args, padding + node.defaults):
            self.write(comma)
            comma = ', '
            self.visit(arg)
            if default is not None:
                self.write('=')
                self.visit(default)
        if node.vararg is not None:
            self.write(comma)
            comma = ', '
            self.write('*' + node.vararg)
        if node.kwarg is not None:
            self.write(comma)
            comma = ', '
            self.write('**' + node.kwarg)

    # Visitors
    
    def visit_Assert(self, node):
        self.newline(node)
        self.write('assert ')
        self.visit(node.test)
        if node.msg:
            self.write(', ')
            self.visit(node.msg)

    def visit_Assign(self, node):
        self.newline(node)
        comma = ''
        for target in node.targets:
            self.write(comma)
            comma = ', '
            if isinstance(target, Tuple):
                self.visit_Tuple(target, parens=False)
            else:
                self.visit(target)
        self.write(' = ')
        if isinstance(node.value, Tuple):
            self.visit_Tuple(node.value, parens=False)
        else:
            self.visit(node.value)

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.write('.' + node.attr)

    def visit_AugAssign(self, node):
        self.newline(node)
        self.visit(node.target)
        self.write(SYMBOLS[type(node.op)].rstrip() + '= ')
        self.visit(node.value)

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.write(' %s ' % SYMBOLS[type(node.op)])
        self.visit(node.right)

    def visit_BoolOp(self, node):
        self.write('(')
        for idx, value in enumerate(node.values):
            if idx:
                self.write(' %s ' % SYMBOLS[type(node.op)])
            self.visit(value)
        self.write(')')

    def visit_Break(self, node):
        self.newline(node)
        self.write('break')

    def visit_Bytes(self, node):
        self.write(repr(node.s))

    def visit_Call(self, node):
        self.visit(node.func)
        self.write('(')
        comma = ''
        for arg in node.args:
            self.write(comma)
            comma = ', '
            self.visit(arg)
        for keyword in node.keywords:
            self.write(comma)
            comma = ', '
            self.write(keyword.arg + '=')
            self.visit(keyword.value)
        if node.starargs is not None:
            self.write(comma)
            comma = ', '
            self.write('*')
            self.visit(node.starargs)
        if node.kwargs is not None:
            self.write(comma)
            comma = ', '
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

    def visit_ClassDef(self, node):
        have_args = False
        def paren_or_comma():
            if have_args:
                self.write(', ')
            else:
                have_args = True
                self.write('(')

        self.newline(extra=2)
        self.decorators(node)
        self.newline(node)
        self.write('class %s' % node.name)
        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        # XXX: the if here is used to keep this module compatible
        #      with python 2.6.
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.write(keyword.arg + '=')
                self.visit(keyword.value)
            if node.starargs is not None:
                paren_or_comma()
                self.write('*')
                self.visit(node.starargs)
            if node.kwargs is not None:
                paren_or_comma()
                self.write('**')
                self.visit(node.kwargs)
        self.write('):' if have_args else ':')
        self.body(node.body)

    def visit_Compare(self, node):
        #self.write('(')
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.write(' %s ' % SYMBOLS[type(op)])
            self.visit(right)
        #self.write(')')

    def visit_Continue(self, node):
        self.newline(node)
        self.write('continue')

    def visit_Delete(self, node):
        self.newline(node)
        self.write('del ')
        for idx, target in enumerate(node.targets):
            if idx:
                self.write(', ')
            self.visit(target)

    def visit_Dict(self, node):
        self.write('{')
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.write(', ')
            self.visit(key)
            self.write(': ')
            self.visit(value)
        self.write('}')

    def visit_DictComp(self, node):
        self.write('{')
        self.visit(node.key)
        self.write(': ')
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.write('}')

    def visit_Ellipsis(self, node):
        #self.write('Ellipsis')
        self.write('...')

    def visit_ExceptHandler(self, node):
        self.newline(node)
        self.write('except')
        if node.type:
            self.write(' ')
            self.visit(node.type)
            if node.name:
                self.write(', ')
                #self.write(' as ')
                self.visit(node.name)
        self.write(':')
        self.body(node.body)

    def visit_Exec(self, node):
        self.newline(node)
        self.write('exec ')
        self.visit(node.body)
        if node.globals and node.locals:
            self.write(' in ')
            self.visit(node.globals)
            self.write(', ')
            self.visit(node.locals)
        elif node.globals:
            self.write(' in ')
            self.visit(node.globals)
        elif node.locals:
            self.write(' in ')
            self.visit(node.locals)

    def visit_Expr(self, node):
        'Expression statement'
        self.newline(node)
        self.visit(node.value)

    def visit_ExtSlice(self, node):
        for idx, item in node.dims:
            if idx:
                self.write(', ')
            self.visit(item)

    def visit_For(self, node):
        self.newline(node)
        self.write('for ')
        if isinstance(node.target, Tuple):
            self.visit_Tuple(node.target, parens=False)
        else:
            self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        self.write(':')
        self.body_else(node)

    def visit_FunctionDef(self, node):
        self.newline(extra=1)
        self.decorators(node)
        self.newline(node)
        self.write('def %s(' % node.name)
        self.signature(node.args)
        self.write('):')
        self.body(node.body)

    def visit_GeneratorExp(self, node):
        self.generator(node, '[]')

    def visit_Global(self, node):
        self.newline(node)
        self.write('global ' + ', '.join(node.names))

    def visit_If(self, node, el=''):
        self.newline(node)
        self.write(el + 'if ')
        self.visit(node.test)
        self.write(':')
        self.body(node.body)
        if node.orelse:
            node = node.orelse        
            if isinstance(node[0], If):
                self.visit(node[0], 'el')
            else:
                self.newline()
                self.lineno = self.getLineNo('else', self.lineno)
                self.write('else:')
                self.body(node)

    def visit_IfExp(self, node):
        self.visit(node.body)
        self.write(' if ')
        self.visit(node.test)
        self.write(' else ')
        self.visit(node.orelse)

    def visit_Import(self, node):
        self.newline(node)
        self.write('import ')
        for item in node.names[:-1]:
            self.visit(item)
            self.write(', ')
        self.visit(node.names[-1])

    def visit_ImportFrom(self, node):
        self.newline(node)
        self.write('from %s%s import ' % ('.' * node.level, node.module))
        for idx, item in enumerate(node.names):
            if idx:
                self.write(', ')
            self.visit(item)

    def visit_Lambda(self, node):
        self.write('lambda ')
        self.signature(node.args)
        self.write(': ')
        self.visit(node.body)

    def visit_List(self, node):
        self.sequence(node, '[]')
        
    def visit_ListComp(self, node):
        self.generator(node, '[]')

    def visit_Module(self, node):
        self.visit(node.body)

    def visit_Name(self, node):
        self.write(node.id)

    def visit_Nonlocal(self, node):
        self.newline(node)
        self.write('nonlocal ' + ', '.join(node.names))

    def visit_Num(self, node):
        self.write(repr(node.n))

    def visit_Pass(self, node):
        self.newline(node)
        self.write('pass')

    def visit_Print(self, node):
        # XXX: python 2.6 only
        self.newline(node)
        self.write('print ')
        want_comma = False
        if node.dest is not None:
            self.write(' >> ')
            self.visit(node.dest)
            want_comma = True
        for value in node.values:
            if want_comma:
                self.write(', ')
            self.visit(value)
            want_comma = True
        if not node.nl:
            self.write(',')

    def visit_Raise(self, node):
        # XXX: Python 2.6 / 3.0 compatibility
        self.newline(node)
        self.write('raise')
        if hasattr(node, 'exc') and node.exc is not None:
            self.write(' ')
            self.visit(node.exc)
            if node.cause is not None:
                self.write(' from ')
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.write(', ')
                self.visit(node.inst)
            if node.tback is not None:
                self.write(', ')
                self.visit(node.tback)

    def visit_Repr(self, node):
        # XXX: python 2.6 only
        self.write('`')
        self.visit(node.value)
        self.write('`')

    def visit_Return(self, node):
        self.newline(node)
        self.write('return')
        if node.value is not None:
            self.write(' ')
            self.visit(node.value)

    def visit_Set(self, node):
        self.sequence(node, '{}')

    def visit_SetComp(self, node):
        self.generator(node, '[]')

    def visit_Slice(self, node):
        if node.lower is not None:
            self.visit(node.lower)
        self.write(':')
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.write(':')
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)

    def visit_Str(self, node):
        s = node.s
        if '\n' in s:
            lines = s.splitlines(1)
            if "'''" not in s and not s.endswith("'"):
                if repr(s).startswith("u'"):
                    self.write('u')
                self.write("'''")
                for line in lines:
                    self.write(line)
                    self.code.append('')
                self.code.pop()
                self.write("'''")
            elif '"""' not in s and not s.endswith('"'):
                if repr(s).startswith("u'"):
                    self.write('u')
                self.write('"""')
                for line in lines:
                    self.write(line)
                    self.code.append('')
                self.code.pop()
                self.write('"""')
            else:
                self.write(repr(node.s))
                #self.write("'''" + s.replace("'''", "\'\'\'")  + "'''")
                #print dump(node)
                #raise
                self.code += [''] * s.count('\n')
        else:
            self.write(repr(node.s))

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.write('[')
        self.visit(node.slice)
        self.write(']')

    def visit_TryExcept(self, node):
        self.newline(node)
        self.write('try:')
        self.body(node.body)
        for handler in node.handlers:
            self.visit(handler)

    def visit_TryFinally(self, node):
        self.newline(node)
        self.write('try:')
        self.body(node.body)
        self.newline(node)
        self.write('finally:')
        self.body(node.finalbody)

    def visit_Tuple(self, node, parens=True):
        if parens: self.write('(')
        comma = ''
        for item in node.elts:
            self.write(comma)
            comma = ', '
            self.visit(item)
        if len(node.elts) == 1:
            self.write(',')
        if parens: self.write(')')

    def visit_UnaryOp(self, node):
        self.write('(')
        op = SYMBOLS[type(node.op)]
        self.write(op)
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_While(self, node):
        self.newline(node)
        self.write('while ')
        self.visit(node.test)
        self.write(':')
        self.body_else(node)

    def visit_With(self, node):
        self.newline(node)
        self.write('with ')
        self.visit(node.context_expr)
        if node.optional_vars is not None:
            self.write(' as ')
            self.visit(node.optional_vars)
        self.write(':')
        self.body(node.body)

    def visit_Yield(self, node):
        self.write('yield ')
        self.visit(node.value)

    # Helper Visitors - are these used?

    def visit_alias(self, node):
        self.write(node.name)
        if node.asname is not None:
            self.write(' as ' + node.asname)

    def visit_comprehension(self, node):
        self.write(' for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.write(' if ')
                self.visit(if_)




def test(modules=None):
    import os
    if not modules:
        #d = 'C:\\Python25\\Lib\\'
        d = '/usr/lib/python2.6/'
        modules = [d + f for f in os.listdir(d) if f.endswith('.py')]
    for f in modules:
        msg = '%s...' % os.path.basename(f)
        ast = parse(file(f).read())
        #c = CommentAdder(f)
        #c.visit(ast)
        c = CodeParser(f)
        '''
        if f == 'parser_test_source.py':
            pass
            #print dump(ast, 1)
            #from pprint_ast import pprintAst
            #pprintAst(ast)
        try:
            file('output.py', 'w').write('\n'.join(map(str, c.result)))
        except:
            msg += 'failed to converting AST back to python code'
            print msg;raise
        try:
            if f == 'parser_test_source.py':
                print file('output.py').read()   # see the results
            parse(file('output.py').read())
            msg += 'OK'
        except:
            msg += 'failed to parse generated code'
            print msg;raise
        '''
        print msg




if __name__ == '__main__':
    f = 'parser_test_source.py'
    #f = 'C:\\Python25\\Lib\\smtpd.py'
    #f = '/usr/lib/python2.6/difflib.py'

    if len(sys.argv) == 2:
        if sys.argv[1].endswith('.py'):
            f = sys.argv[1]
        test([f])
    else:
        test([f])




'''


Node names from _ast.py

'''

x = '''
Add
And
Assert
Assign
Attribute
AugAssign
AugLoad
AugStore
BinOp
BitAnd
BitOr
BitXor
BoolOp
Break
Call
ClassDef
Compare
Continue
Del
Delete
Dict
Div
Ellipsis
Eq
ExceptHandler
Exec
Expr
Expression
ExtSlice
FloorDiv
For
FunctionDef
GeneratorExp
Global
Gt
GtE
If
IfExp
Import
ImportFrom
In
Index
Interactive
Invert
Is
IsNot
LShift
Lambda
List
ListComp
Load
Lt
LtE
Mod
Module
Mult
Name
Not
NotEq
NotIn
Num
Or
Param
Pass
Pow
Print
RShift
Raise
Repr
Return
Slice
Store
Str
Sub
Subscript
Suite
TryExcept
TryFinally
Tuple
UAdd
USub
UnaryOp
While
With
Yield



syms = [k.__name__ for k in SYMBOLS.keys()]
for n in x.split('\n'):
    s = n.strip()
    if s:
        if 'visit_' + s not in dir(CodeParser):
            if s not in syms:
                print 'missing', n.strip()

missing AugLoad
missing AugStore
missing Del
missing Expression
missing Index
missing Interactive
missing Load
missing Module
missing Param
missing Store
missing Suite






'''






