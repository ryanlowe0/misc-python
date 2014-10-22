#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from ast import *
from tokenize import generate_tokens, COMMENT, NL, NEWLINE



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

       Based on Python's AST tree, but with enough extra info to represent
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
        print [(t[1], i+1) for i, line in enumerate(self.tokens) for t in line if t]
        self.visit(self.ast)

    def getToken(self, tok, node):
        if not tok: return
        if not hasattr(node, 'tokens'):
            node.tokens = []
        for lineno in range(node.lineno - 1, len(self.tokens)):
            for i, t in enumerate(self.tokens[lineno]):
                if t[1] == tok:
                    # pop matching token so it cant be matched again
                    print self.tokens[lineno][i], node.__class__.__name__
                    node.tokens.append(self.tokens[lineno].pop(i))
        print 'token not found: %s' % tok, node.__class__.__name__

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
            self.addToken('else', node.orelse)
            self.addToken(':', node.orelse)
            self.body(node.orelse)

    def decorators(self, node):
        first = True
        for decorator in node.decorator_list:
            # newline not needed for 1st because funcdef already adds 2
            first = False
            self.addToken('@', node.lineno)
            self.visit(decorator)

    def generator(self, node, wrapper):
        # wrapper = [], (), or {}
        self.addToken(wrapper[0], node.lineno)
        self.visit(node.elt)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.addToken(wrapper[1], node.lineno)

    def sequence(self, node, wrapper):
        self.addToken(wrapper[0], node.lineno)
        comma = ''
        for item in node.elts:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.visit(item)
        self.addToken(wrapper[1], node.lineno)

    def signature(self, node):
        padding = [None] * (len(node.args) - len(node.defaults))
        comma = ''
        for arg, default in zip(node.args, padding + node.defaults):
            self.addToken(comma, node.lineno)
            comma = ', '
            self.visit(arg)
            if default is not None:
                self.addToken('=', node.lineno)
                self.visit(default)
        if node.vararg is not None:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.addToken('*', node.lineno)
            self.addToken(node.vararg, node.lineno)
        if node.kwarg is not None:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.addToken('**', node.lineno)
            self.addToken(node.kwarg, node.lineno)

    # Visitors
    
    def visit_Assert(self, node):
        self.addToken('assert', node.lineno)
        self.visit(node.test)
        if node.msg:
            self.addToken(',', node.lineno)
            self.visit(node.msg)

    def visit_Assign(self, node):
        comma = ''
        for target in node.targets:
            self.addToken(comma, node.lineno)
            comma = ','
            if isinstance(target, Tuple):
                self.visit_Tuple(target, parens=False)
            else:
                self.visit(target)
        self.addToken('=', node.lineno)
        if isinstance(node.value, Tuple):
            self.visit_Tuple(node.value, parens=False)
        else:
            self.visit(node.value)

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.addToken('.' + node.attr, node.lineno)

    def visit_AugAssign(self, node):
        self.visit(node.target)
        self.addToken(SYMBOLS[type(node.op)] + '=', node.lineno)
        self.visit(node.value)

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.addToken(SYMBOLS[type(node.op)], node.lineno)
        self.visit(node.right)

    def visit_BoolOp(self, node):
        self.addToken('(', node.lineno)
        for idx, value in enumerate(node.values):
            if idx:
                self.addToken(SYMBOLS[type(node.op)], node.lineno)
            self.visit(value)
        self.addToken(')', node.lineno)

    def visit_Break(self, node):
        self.addToken('break', node.lineno)

    def visit_Bytes(self, node):
        self.addToken(repr(node.s, node.lineno))

    def visit_Call(self, node):
        self.visit(node.func)
        self.addToken('(', node.lineno)
        comma = ''
        for arg in node.args:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.visit(arg)
        for keyword in node.keywords:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.addToken(keyword.arg, node.lineno)
            self.addToken('=', node.lineno)
            self.visit(keyword.value)
        if node.starargs is not None:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.addToken('*', node.lineno)
            self.visit(node.starargs)
        if node.kwargs is not None:
            self.addToken(comma, node.lineno)
            comma = ', '
            self.addToken('**', node.lineno)
            self.visit(node.kwargs)
        self.addToken(')', node.lineno)

    def visit_ClassDef(self, node):
        have_args = False
        def paren_or_comma():
            if have_args:
                self.addToken(',', node.lineno)
            else:
                have_args = True
                self.addToken('(', node.lineno)

        self.decorators(node)
        self.addToken('class', node.lineno)
        self.addToken(node.name, node.lineno)
        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        # XXX: the if here is used to keep this module compatible
        #      with python 2.6.
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.addToken(keyword.arg, node.lineno)
                self.addToken('=', node.lineno)
                self.visit(keyword.value)
            if node.starargs is not None:
                paren_or_comma()
                self.addToken('*', node.lineno)
                self.visit(node.starargs)
            if node.kwargs is not None:
                paren_or_comma()
                self.addToken('**', node.lineno)
                self.visit(node.kwargs)
        if have_args: self.addToken(')', node.lineno)
        self.addToken(':', node.lineno)
        self.body(node.body)

    def visit_Compare(self, node):
        #self.addToken('(', node.lineno)
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.addToken(SYMBOLS[type(op)], node.lineno)
            self.visit(right)
        #self.addToken(')', node.lineno)

    def visit_Continue(self, node):
        self.addToken('continue', node.lineno)

    def visit_Delete(self, node):
        self.addToken('del', node.lineno)
        for idx, target in enumerate(node.targets):
            if idx:
                self.addToken(',', node.lineno)
            self.visit(target)

    def visit_Dict(self, node):
        self.addToken('{', node.lineno)
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.addToken(',', node.lineno)
            self.visit(key)
            self.addToken(':', node.lineno)
            self.visit(value)
        self.addToken('}', node.lineno)

    def visit_DictComp(self, node):
        self.addToken('{', node.lineno)
        self.visit(node.key)
        self.addToken(':', node.lineno)
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.addToken('}', node.lineno)

    def visit_Ellipsis(self, node):
        #self.addToken('Ellipsis', node.lineno)
        self.addToken('...', node.lineno)

    def visit_ExceptHandler(self, node):
        self.addToken('except', node.lineno)
        if node.type:
            self.visit(node.type)
            if node.name:
                self.addToken(',', node.lineno)
                #self.addToken('as', node.lineno)
                self.visit(node.name)
        self.addToken(':', node.lineno)
        self.body(node.body)

    def visit_Exec(self, node):
        self.addToken('exec', node.lineno)
        self.visit(node.body)
        if node.globals and node.locals:
            self.addToken('in', node.lineno)
            self.visit(node.globals)
            self.addToken(',', node.lineno)
            self.visit(node.locals)
        elif node.globals:
            self.addToken('in', node.lineno)
            self.visit(node.globals)
        elif node.locals:
            self.addToken('in', node.lineno)
            self.visit(node.locals)

    def visit_Expr(self, node):
        'Expression statement'
        self.generic_visit(node)

    def visit_ExtSlice(self, node):
        for idx, item in node.dims:
            if idx:
                self.addToken(',', node.lineno)
            self.visit(item)

    def visit_For(self, node):
        self.addToken('for', node.lineno)
        if isinstance(node.target, Tuple):
            self.visit_Tuple(node.target, parens=False)
        else:
            self.visit(node.target)
        self.addToken('in', node.lineno)
        self.visit(node.iter)
        self.addToken(':', node.lineno)
        self.body_else(node)

    def visit_FunctionDef(self, node):
        self.decorators(node)
        self.addToken('def', node.lineno)
        self.addToken('(', node.lineno)
        self.addToken(node.name, node.lineno)
        self.signature(node.args)
        self.addToken(')', node.lineno)
        self.addToken(':', node.lineno)
        self.body(node.body)

    def visit_GeneratorExp(self, node):
        self.generator(node, '[]')

    def visit_Global(self, node):
        self.addToken('global', node.lineno)
        comma = ''
        for name in node.names:
            self.addToken(comma, node.lineno)
            comma = ','
            self.addToken(name, node.lineno)

    def visit_If(self, node, el=''):
        self.addToken(el + 'if ', node.lineno)
        self.visit(node.test)
        self.addToken(':', node.lineno)
        self.body(node.body)
        if node.orelse:
            node = node.orelse        
            if isinstance(node[0], If):
                self.visit(node[0], 'el')
            else:
                self.addToken('else', node.lineno)
                self.addToken(':', node.lineno)
                self.body(node)

    def visit_IfExp(self, node):
        self.visit(node.body)
        self.addToken('if', node.lineno)
        self.visit(node.test)
        self.addToken('else', node.lineno)
        self.visit(node.orelse)

    def visit_Import(self, node):
        self.addToken('import', node.lineno)
        for item in node.names[:-1]:
            self.visit(item)
            self.addToken(',', node.lineno)
        self.visit(node.names[-1])

    def visit_ImportFrom(self, node):
        self.addToken('from', node.lineno)
        self.addToken('.' * node.level, node.lineno)
        self.addToken(node.module, node.lineno)
        self.addToken('import', node.lineno)
        for idx, item in enumerate(node.names):
            if idx:
                self.addToken(',', node.lineno)
            self.visit(item)

    def visit_Lambda(self, node):
        self.addToken('lambda', node.lineno)
        self.signature(node.args)
        self.addToken(':', node.lineno)
        self.visit(node.body)

    def visit_List(self, node):
        self.sequence(node, '[]')
        
    def visit_ListComp(self, node):
        self.generator(node, '[]')

    def visit_Module(self, node):
        self.visit(node.body)

    def visit_Name(self, node):
        self.addToken(node.id, node.lineno)

    def visit_Nonlocal(self, node):
        self.addToken('nonlocal', node.lineno)
        for idx, name in node.names:
            if idx:
                self.addToken(',', node.lineno)
            self.addToken(name, node.lineno)

    def visit_Num(self, node):
        self.addToken(repr(node.n), node.lineno)

    def visit_Pass(self, node):
        self.addToken('pass', node.lineno)

    def visit_Print(self, node):
        # XXX: python 2.6 only
        self.addToken('print', node.lineno)
        want_comma = False
        if node.dest is not None:
            self.addToken('>>', node.lineno)
            self.visit(node.dest)
            want_comma = True
        for value in node.values:
            if want_comma:
                self.addToken(',', node.lineno)
            self.visit(value)
            want_comma = True
        if not node.nl:
            self.addToken(',', node.lineno)

    def visit_Raise(self, node):
        # XXX: Python 2.6 / 3.0 compatibility
        self.addToken('raise', node.lineno)
        if hasattr(node, 'exc') and node.exc is not None:
            self.visit(node.exc)
            if node.cause is not None:
                self.addToken('from', node.lineno)
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.addToken(',', node.lineno)
                self.visit(node.inst)
            if node.tback is not None:
                self.addToken(',', node.lineno)
                self.visit(node.tback)

    def visit_Repr(self, node):
        # XXX: python 2.6 only
        self.addToken('`', node.lineno)
        self.visit(node.value)
        self.addToken('`', node.lineno)

    def visit_Return(self, node):
        self.addToken('return', node.lineno)
        if node.value is not None:
            self.visit(node.value)

    def visit_Set(self, node):
        self.sequence(node, '{}')

    def visit_SetComp(self, node):
        self.generator(node, '[]')

    def visit_Slice(self, node):
        if node.lower is not None:
            self.visit(node.lower)
        self.addToken(':', node.lineno)
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.addToken(':', node.lineno)
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)

    def visit_Str(self, node):
        s = node.s
        if '\n' in s:
            lines = s.splitlines(1)
            if "'''" not in s and not s.endswith("'"):
                if repr(s).startswith("u'"):
                    self.addToken('u', node.lineno)
                self.addToken("'''", node.lineno)
                for line in lines:
                    self.addToken(line, node.lineno)
                    self.code.append('')
                self.code.pop()
                self.addToken("'''", node.lineno)
            elif '"""' not in s and not s.endswith('"'):
                if repr(s).startswith("u'"):
                    self.addToken('u', node.lineno)
                self.addToken('"""', node.lineno)
                for line in lines:
                    self.addToken(line, node.lineno)
                    self.code.append('')
                self.code.pop()
                self.addToken('"""', node.lineno)
            else:
                self.addToken(repr(node.s, node.lineno))
                #self.addToken("'''" + s.replace("'''", "\'\'\'", node.lineno)  + "'''")
                #print dump(node)
                #raise
                self.code += [''] * s.count('\n')
        else:
            self.addToken(repr(node.s, node.lineno))

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.addToken('[', node.lineno)
        self.visit(node.slice)
        self.addToken(']', node.lineno)

    def visit_TryExcept(self, node):
        self.addToken('try', node.lineno)
        self.addToken(':', node.lineno)
        self.body(node.body)
        for handler in node.handlers:
            self.visit(handler)

    def visit_TryFinally(self, node):
        self.addToken('try', node.lineno)
        self.addToken(':', node.lineno)
        self.body(node.body)
        self.addToken('finally', node.lineno)
        self.addToken(':', node.lineno)
        self.body(node.finalbody)

    def visit_Tuple(self, node, parens=True):
        if parens: self.addToken('(', node.lineno)
        comma = ''
        for item in node.elts:
            self.addToken(comma, node.lineno)
            comma = ','
            self.visit(item)
        if len(node.elts) == 1:
            self.addToken(',', node.lineno)
        if parens: self.addToken(')', node.lineno)

    def visit_UnaryOp(self, node):
        self.addToken('(', node.lineno)
        self.addToken(SYMBOLS[type(node.op)], node.lineno)
        self.visit(node.operand)
        self.addToken(')', node.lineno)

    def visit_While(self, node):
        self.addToken('while', node.lineno)
        self.visit(node.test)
        self.addToken(':', node.lineno)
        self.body_else(node)

    def visit_With(self, node):
        self.addToken('with', node.lineno)
        self.visit(node.context_expr)
        if node.optional_vars is not None:
            self.addToken('as', node.lineno)
            self.visit(node.optional_vars)
        self.addToken(':', node.lineno)
        self.body(node.body)

    def visit_Yield(self, node):
        self.addToken('yield', node.lineno)
        self.visit(node.value)

    # Helper Visitors - are these used?

    def visit_alias(self, node):
        self.addToken(node.name, node.lineno)
        if node.asname is not None:
            self.addToken('as' + node.asname, node.lineno)

    def visit_comprehension(self, node):
        self.addToken('for', node.lineno)
        self.visit(node.target)
        self.addToken('in', node.lineno)
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.addToken('if', node.lineno)
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








