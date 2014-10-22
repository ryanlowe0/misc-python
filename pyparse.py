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


class Node(object):
    '''
    '''
    def __init__(self, **data):
        self.__dict__.update(data)

    def __getitem__(self, item):
        return getattr(self, item)
                
    def __setitem__(self, item, value):
        setattr(self, item, value)


class Code(object):
    '''Self-Aware Code object.

       Based on Python's AST tree, but with enough extra info to output
       source code as the original author wrote it
       
    '''



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
        #print ' '.join([t[1] for i, line in enumerate(self.tokens) for t in
        #line if t])
        self.visit(self.ast)

    def addToken(self, tok, node):
        if not tok: return
        #print self.tokens
        #if not hasattr(node, 'lineno'):
        #    print 'addToken'
        #    print tok
        #    print node.__class__.__name__
        #    print type(node)
        #    print dir(node)
        #    raise
        if not hasattr(node, 'tokens'):
            node.tokens = []
            node._attributes = tuple(list(node._attributes) + ['tokens'])
        print repr(tok)
        for lineno in range(node.lineno - 1, len(self.tokens)):
            if lineno > len(self.tokens) - 1:
                break
            for i, t in enumerate(self.tokens[lineno]):
                print i
                print t[1]
                if tok == t[1]:
                    # pop matching token so it cant be matched again
                    #print self.tokens[lineno][i], node.__class__.__name__
                    node.tokens.append(self.tokens[lineno].pop(i))
                    return
            
        #print 'token "%s" not found for %s\'s line. Looking backwards...' % \
        #    (tok, node.__class__.__name__)
        #for lineno in range(node.lineno - 1, 0, -1):
        for lineno in range(len(self.tokens) - 1, 0, -1):
            if lineno > len(self.tokens) - 1:
                break
            for i, t in enumerate(self.tokens[lineno]):
                print i
                print t[1]
                if t[1] == tok:
                #if repr(t[1]) == repr(tok):
                #if tok == t[1]:
                    # pop matching token so it cant be matched again
                    #print self.tokens[lineno][i], node.__class__.__name__
                    node.tokens.append(self.tokens[lineno].pop(i))
                    return
        print 'token still not found'
        print '-'*30
        print tok
        print '-'*30
        print repr(tok)
        print '-'*30
        #print ' '.join(['"%s"' % t[1] for i, line in enumerate(self.tokens) for t in line if t])
        print self.tokens
        print

    # Base Visitor
    
    def visit(self, node, **kw):
        #method = 'none'
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, **kw)

    def visit_list(self, items):
        for item in items:
            self.visit(item)

    def generic_visit(self, node, **kw):
        print dir(node)
        raise NotImplementedError('visit_%s not defined' % node.__class__.__name__)
        kw['parent'] = kw.get('parent', node)
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item, **kw)
            elif isinstance(value, AST):
                self.visit(value, **kw)

    # Extracted visit patterns

    def body(self, statements):
        for stmt in statements:
            self.visit(stmt)

    def body_else(self, node):
        self.body(node.body)
        if node.orelse:
            self.addToken('else', node)
            self.addToken(':', node)
            self.body(node.orelse)

    def decorators(self, node):
        first = True
        for decorator in node.decorator_list:
            # newline not needed for 1st because funcdef already adds 2
            first = False
            self.addToken('@', node)
            self.visit(decorator)

    def generator(self, node, wrapper):
        # wrapper = [], (), or {}
        self.addToken(wrapper[0], node)
        self.visit(node.elt)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.addToken(wrapper[1], node)

    def sequence(self, node, wrapper):
        self.addToken(wrapper[0], node)
        comma = ''
        for item in node.elts:
            self.addToken(comma, node)
            comma = ','
            self.visit(item)
        self.addToken(wrapper[1], node)

    def signature(self, node):
        padding = [None] * (len(node.args) - len(node.defaults))
        comma = ''
        for arg, default in zip(node.args, padding + node.defaults):
            self.addToken(comma, node)
            comma = ','
            self.visit(arg)
            if default is not None:
                self.addToken('=', node)
                self.visit(default)
        if node.vararg is not None:
            self.addToken(comma, node)
            comma = ','
            self.addToken('*', node)
            self.addToken(node.vararg, node)
        if node.kwarg is not None:
            self.addToken(comma, node)
            comma = ','
            self.addToken('**', node)
            self.addToken(node.kwarg, node)

    # Visitors
    
    def visit_arguments(self, node):
        print 'visit_arguments'
        print tok
        print node.__class__.__name__
        print type(node)
        print dir(node)
        raise

    def visit_Assert(self, node):
        self.addToken('assert', node)
        self.visit(node.test)
        if node.msg:
            self.addToken(',', node)
            self.visit(node.msg)

    def visit_Assign(self, node):
        comma = ''
        for target in node.targets:
            self.addToken(comma, node)
            comma = ','
            if isinstance(target, Tuple):
                self.visit_Tuple(target, parens=False)
            else:
                self.visit(target)
        self.addToken('=', node)
        if isinstance(node.value, Tuple):
            self.visit_Tuple(node.value, parens=False)
        else:
            self.visit(node.value)

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.addToken('.', node)
        self.addToken(node.attr, node)

    def visit_AugAssign(self, node):
        self.visit(node.target)
        self.addToken(SYMBOLS[type(node.op)] + '=', node)
        self.visit(node.value)

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.addToken(SYMBOLS[type(node.op)], node)
        self.visit(node.right)

    def visit_BoolOp(self, node):
        self.addToken('(', node)
        for idx, value in enumerate(node.values):
            if idx:
                self.addToken(SYMBOLS[type(node.op)], node)
            self.visit(value)
        self.addToken(')', node)

    def visit_Break(self, node):
        self.addToken('break', node)

    def visit_Bytes(self, node):
        self.addToken(repr(node.s), node)

    def visit_Call(self, node):
        self.visit(node.func)
        self.addToken('(', node)
        comma = ''
        for arg in node.args:
            self.addToken(comma, node)
            comma = ','
            self.visit(arg)
        for keyword in node.keywords:
            self.addToken(comma, node)
            comma = ','
            self.addToken(keyword.arg, node)
            self.addToken('=', node)
            self.visit(keyword.value)
        if node.starargs is not None:
            self.addToken(comma, node)
            comma = ','
            self.addToken('*', node)
            self.visit(node.starargs)
        if node.kwargs is not None:
            self.addToken(comma, node)
            comma = ','
            self.addToken('**', node)
            self.visit(node.kwargs)
        self.addToken(')', node)

    def visit_ClassDef(self, node):
        have_args = False
        def paren_or_comma():
            if have_args:
                self.addToken(',', node)
            else:
                have_args = True
                self.addToken('(', node)

        self.decorators(node)
        self.addToken('class', node)
        self.addToken(node.name, node)
        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        # XXX: the if here is used to keep this module compatible
        #      with python 2.6.
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.addToken(keyword.arg, node)
                self.addToken('=', node)
                self.visit(keyword.value)
            if node.starargs is not None:
                paren_or_comma()
                self.addToken('*', node)
                self.visit(node.starargs)
            if node.kwargs is not None:
                paren_or_comma()
                self.addToken('**', node)
                self.visit(node.kwargs)
        if have_args: self.addToken(')', node)
        self.addToken(':', node)
        self.body(node.body)

    def visit_Compare(self, node):
        #self.addToken('(', node)
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.addToken(SYMBOLS[type(op)], node)
            self.visit(right)
        #self.addToken(')', node)

    def visit_Continue(self, node):
        self.addToken('continue', node)

    def visit_Delete(self, node):
        self.addToken('del', node)
        for idx, target in enumerate(node.targets):
            if idx:
                self.addToken(',', node)
            self.visit(target)

    def visit_Dict(self, node):
        self.addToken('{', node)
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.addToken(',', node)
            self.visit(key)
            self.addToken(':', node)
            self.visit(value)
        self.addToken('}', node)

    def visit_DictComp(self, node):
        self.addToken('{', node)
        self.visit(node.key)
        self.addToken(':', node)
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.addToken('}', node)

    def visit_Ellipsis(self, node):
        #self.addToken('Ellipsis', node)
        self.addToken('...', node)

    def visit_ExceptHandler(self, node):
        self.addToken('except', node)
        if node.type:
            self.visit(node.type)
            if node.name:
                self.addToken(',', node)
                #self.addToken('as', node)
                self.visit(node.name)
        self.addToken(':', node)
        self.body(node.body)

    def visit_Exec(self, node):
        self.addToken('exec', node)
        self.visit(node.body)
        if node.globals and node.locals:
            self.addToken('in', node)
            self.visit(node.globals)
            self.addToken(',', node)
            self.visit(node.locals)
        elif node.globals:
            self.addToken('in', node)
            self.visit(node.globals)
        elif node.locals:
            self.addToken('in', node)
            self.visit(node.locals)

    def visit_Expr(self, node):
        'Expression statement'
        self.visit(node.value)

    def visit_ExtSlice(self, node):
        for idx, item in node.dims:
            if idx:
                self.addToken(',', node)
            self.visit(item)

    def visit_For(self, node):
        self.addToken('for', node)
        if isinstance(node.target, Tuple):
            self.visit_Tuple(node.target, parens=False)
        else:
            self.visit(node.target)
        self.addToken('in', node)
        self.visit(node.iter)
        self.addToken(':', node)
        self.body_else(node)

    def visit_FunctionDef(self, node):
        self.decorators(node)
        self.addToken('def', node)
        self.addToken('(', node)
        self.addToken(node.name, node)
        node.args.lineno = node.lineno
        self.signature(node.args)
        self.addToken(')', node)
        self.addToken(':', node)
        self.body(node.body)

    def visit_GeneratorExp(self, node):
        self.generator(node, '[]')

    def visit_Global(self, node):
        self.addToken('global', node)
        comma = ''
        for name in node.names:
            self.addToken(comma, node)
            comma = ','
            self.addToken(name, node)

    def visit_If(self, node, el=''):
        self.addToken(el + 'if', node)
        self.visit(node.test)
        self.addToken(':', node)
        self.body(node.body)
        if node.orelse:
            node = node.orelse        
            if isinstance(node[0], If):
                self.visit(node[0], 'el')
            else:
                self.addToken('else', node)
                self.addToken(':', node)
                self.body(node)

    def visit_IfExp(self, node):
        self.visit(node.body)
        self.addToken('if', node)
        self.visit(node.test)
        self.addToken('else', node)
        self.visit(node.orelse)

    def visit_Import(self, node):
        self.addToken('import', node)
        for idx, item in enumerate(node.names):
            if idx:
                self.addToken(',', node)
            if not hasattr(item, 'lineno'):
                item.lineno = node.lineno
            self.visit(item)

    def visit_ImportFrom(self, node):
        self.addToken('from', node)
        self.addToken('.' * node.level, node)
        self.addToken(node.module, node)
        self.addToken('import', node)
        for idx, item in enumerate(node.names):
            if idx:
                self.addToken(',', node)
            if not hasattr(item, 'lineno'):
                item.lineno = node.lineno
            self.visit(item)

    def visit_Lambda(self, node):
        self.addToken('lambda', node)
        self.signature(node.args)
        self.addToken(':', node)
        self.visit(node.body)

    def visit_List(self, node):
        self.sequence(node, '[]')
        
    def visit_ListComp(self, node):
        self.generator(node, '[]')

    def visit_Module(self, node):
        self.visit(node.body)

    def visit_Name(self, node):
        self.addToken(node.id, node)

    def visit_Nonlocal(self, node):
        self.addToken('nonlocal', node)
        for idx, name in node.names:
            if idx:
                self.addToken(',', node)
            self.addToken(name, node)

    def visit_Num(self, node):
        self.addToken(repr(node.n), node)

    def visit_Pass(self, node):
        self.addToken('pass', node)

    def visit_Print(self, node):
        # XXX: python 2.6 only
        self.addToken('print', node)
        want_comma = False
        if node.dest is not None:
            self.addToken('>>', node)
            self.visit(node.dest)
            want_comma = True
        for value in node.values:
            if want_comma:
                self.addToken(',', node)
            self.visit(value)
            want_comma = True
        if not node.nl:
            self.addToken(',', node)

    def visit_Raise(self, node):
        # XXX: Python 2.6 / 3.0 compatibility
        self.addToken('raise', node)
        if hasattr(node, 'exc') and node.exc is not None:
            self.visit(node.exc)
            if node.cause is not None:
                self.addToken('from', node)
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.addToken(',', node)
                self.visit(node.inst)
            if node.tback is not None:
                self.addToken(',', node)
                self.visit(node.tback)

    def visit_Repr(self, node):
        # XXX: python 2.6 only
        self.addToken('`', node)
        self.visit(node.value)
        self.addToken('`', node)

    def visit_Return(self, node):
        self.addToken('return', node)
        if node.value is not None:
            self.visit(node.value)

    def visit_Set(self, node):
        self.sequence(node, '{}')

    def visit_SetComp(self, node):
        self.generator(node, '[]')

    def visit_Slice(self, node):
        if node.lower is not None:
            self.visit(node.lower)
        self.addToken(':', node)
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.addToken(':', node)
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)

    def visit_Str(self, node):
        #self.addToken(repr(node.s), node)
        self.addToken(node.s, node)

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.addToken('[', node)
        self.visit(node.slice)
        self.addToken(']', node)

    def visit_TryExcept(self, node):
        self.addToken('try', node)
        self.addToken(':', node)
        self.body(node.body)
        for handler in node.handlers:
            self.visit(handler)

    def visit_TryFinally(self, node):
        self.addToken('try', node)
        self.addToken(':', node)
        self.body(node.body)
        self.addToken('finally', node)
        self.addToken(':', node)
        self.body(node.finalbody)

    def visit_Tuple(self, node, parens=True):
        if parens: self.addToken('(', node)
        comma = ''
        for item in node.elts:
            self.addToken(comma, node)
            comma = ','
            self.visit(item)
        if len(node.elts) == 1:
            self.addToken(',', node)
        if parens: self.addToken(')', node)

    def visit_UnaryOp(self, node):
        self.addToken('(', node)
        self.addToken(SYMBOLS[type(node.op)], node)
        self.visit(node.operand)
        self.addToken(')', node)

    def visit_While(self, node):
        self.addToken('while', node)
        self.visit(node.test)
        self.addToken(':', node)
        self.body_else(node)

    def visit_With(self, node):
        self.addToken('with', node)
        self.visit(node.context_expr)
        if node.optional_vars is not None:
            self.addToken('as', node)
            self.visit(node.optional_vars)
        self.addToken(':', node)
        self.body(node.body)

    def visit_Yield(self, node):
        self.addToken('yield', node)
        self.visit(node.value)

    # Helper Visitors - are these used?

    def visit_alias(self, node):
        self.addToken(node.name, node)
        if node.asname is not None:
            self.addToken('as', node)
            self.addToken(node.asname, node)

    def visit_comprehension(self, node):
        self.addToken('for', node)
        self.visit(node.target)
        self.addToken('in', node)
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.addToken('if', node)
                self.visit(if_)


def dump(node, annotate_fields=True, include_attributes=False):
    """
    Return a formatted dump of the tree in *node*.  This is mainly useful for
    debugging purposes.  The returned string will show the names and the values
    for fields.  This makes the code impossible to evaluate, so if evaluation
is
    wanted *annotate_fields* must be set to False.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    *include_attributes* can be set to True.
    """
    def _format(node):
        if isinstance(node, AST):
            fields = [(a, _format(b)) for a, b in iter_fields(node)]
            rv = '%s(%s' % (node.__class__.__name__, ', '.join(
                ('%s=%s' % field for field in fields)
                if annotate_fields else
                (b for a, b in fields)
            ))
            if include_attributes and node._attributes:
                rv += fields and ', ' or ' '
                for a in node._attributes:
                    if a == 'tokens':
                        x = [t[1] for t in node.tokens]
                    else:
                        x = _format(getattr(node, a))                        
                    rv += '%s=%s' % (a, x) + ', '
                rv = rv.rstrip(', ')
                #rv += ', '.join('%s=%s' % (a, _format(getattr(node, a)))
                #                for a in node._attributes)
            return rv + ')'
        elif isinstance(node, list):
            return '[%s]' % ', '.join(_format(x) for x in node)
        return repr(node)
    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)


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
        if f == 'parser_test_source.py':
            print 'dumping..'
            print dump(c.ast, 1, 1)
            #from pprint_ast import pprintAst
            #pprintAst(ast)

            output = []
            for child in walk(c.ast):
                if 'tokens' in child._attributes:
                    for t in child.tokens:
                        tok = t[1]
                        lineno, col = t[2]
                        while len(output) <= lineno:
                            output.append([])
                        line = output[lineno]
                        while len(line) < col:
                            line.append(' ')
                        line[col:col + len(tok)] = list(tok)
            print output
            print '\n'.join(''.join(line) for line in output)

        '''
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








