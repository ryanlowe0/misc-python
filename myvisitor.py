#!/usr/bin/env python

from tools import *

import sys
import shutil
from compiler.visitor import ASTVisitor
from compiler import parse, walk
from compiler.consts import *



class NotImplementedException(Exception): pass


class UnparsingVisitor(ASTVisitor):
    '''This class walks a Python Abstract Syntax Tree, and outputs
       well formatted source code text.
    '''
    def __init__(self, stream=None, comments={}):
        if stream is None:
            self.stream = sys.stdout
        else:
            self.stream = stream
        self.indents = 0
        self.comments = comments
        #self.v = lambda tree, visitor=self: walk(tree, visitor)
        self.v = self._visit
        ASTVisitor.__init__(self)

    def _visit(self, node):
        if hasattr(node, 'lineno'):
            self.lineno = node.lineno
        return walk(node, self)

    def write(self, data):
        self.stream.write(data)

    def writestring(self, s):
        if "'''" not in s:
            self.write("'''" + s + "'''")
        elif '"""' not in s:
            self.write('"""' + s + '"""')
        else:
            raise
            self.write("'''" + s.replace("'''", "\'\'\'")  + "'''")

    def DEDENT(self):
        # note: a blank line appears before every dedent
        self.indents -= 1
        self.NEWLINE()
            
    def INDENT(self):
        self.indents += 1
        self.NEWLINE()

    def NEWLINE(self):
        if self.lineno in self.comments and \
           self.comments[self.lineno][1] == 'inline':
            self.write(' ' + self.comments[self.lineno][0])
        self.write('\n')
        self.write(' ' * 4 * self.indents)

    def visitBlock(self, block):
        self.INDENT()
        self.v(block)
        self.DEDENT()

    def visitAdd(self, node):
        # Add attributes
        #     left             left operand
        #     right            right operand
        #self.write('(')
        self.v(node.left)
        self.write(' + ')
        self.v(node.right)
        #self.write(')')

    def visitAnd(self, node):
        # And attributes
        #     nodes            list of operands
        for n in node.nodes[:-1]:
            self.v(n)
            self.write(' and ')
        self.v(node.nodes[-1])

    def visitAssAttr(self, node):
        # AssAttr attributes
        #     expr             expression on the left-hand side of the dot
        #     attrname         the attribute name, a string
        #     flags            XXX
        self.v(node.expr)
        #self.v(node.expr, self)
        self.write('.%s' % node.attrname)

    def visitAssList(self, node):
        # AssList attributes
        #     nodes            list of list elements being assigned to
        del_stat = node.nodes[0].flags == OP_DELETE
        if del_stat:
            self.write('del ')
        self.write('[')
        for n in node.nodes[:-1]:
            n.flags = ''    # prevent double-writing 'del'
            self.v(n)
            self.write(', ')
        node.nodes[-1].flags = ''
        self.v(node.nodes[-1])
        self.write(']')
        if del_stat:
            self.NEWLINE()

    def visitAssName(self, node):
        # AssName attributes
        #     name             name being assigned to
        #     flags            XXX
        if node.flags == OP_DELETE:
            self.write('del ')
        self.write(node.name)
        if node.flags == OP_DELETE:
            self.NEWLINE()

    def visitAssTuple(self, node):
        # AssTuple attributes
        #     nodes            list of tuple elements being assigned to
        n = node.nodes[0]               # recurse until node with flags
        while not hasattr(n, 'flags'):  # found. if that is a del, the
            n = n.nodes[0]              # whole stmt is assumed to be a del
        del_stat = n.flags == OP_DELETE
        if del_stat:
            self.write('del ')
        for n in node.nodes[:-1]:
            n.flags = ''    # prevent double-writing 'del'
            self.v(n)
            self.write(', ')
        node.nodes[-1].flags = ''
        self.v(node.nodes[-1])
        if del_stat:
            self.NEWLINE()

    def visitAssert(self, node):
        # Assert attributes
        #     test             the expression to be tested
        #     fail             the value of the AssertionError
        self.write('assert ')
        self.v(node.test)
        if node.fail:
            self.write(', ')
            self.v(node.fail)
        self.NEWLINE()

    def visitAssign(self, node):
        # Assign attributes
        #     nodes            a list of assignment targets, one per equal sign
        #     expr             the value being assigned
        for i in range(len(node.nodes)):
            n = node.nodes[i]
            self.v(n)
            if i < len(node.nodes):
                self.write(' = ')
        self.v(node.expr)
        self.write(' ')
        self.NEWLINE()

    def visitAugAssign(self, node):
        # AugAssign attributes
        #     node             
        #     op               
        #     expr             
        self.v(node.node)
        self.write(' %s ' % node.op)
        self.v(node.expr)
        self.NEWLINE()

    def visitBackquote(self, node):
        # Backquote attributes
        #     expr             
        raise NotImplementedException('visitBackquote')

    def visitBitand(self, node):
        # Bitand attributes
        #     nodes            
        for i in range(len(node.nodes)):
            self.v(node.nodes[i])
            if i < (len(node.nodes) - 1):
                self.write(' & ')

    def visitBitor(self, node):
        # Bitor attributes
        #     nodes            
        for i in range(len(node.nodes)):
            self.v(node.nodes[i])
            if i < (len(node.nodes) - 1):
                self.write(' | ')

    def visitBitxor(self, node):
        # Bitxor attributes
        #     nodes            
        for i in range(len(node.nodes)):
            self.v(node.nodes[i])
            if i < (len(node.nodes) - 1):
                self.write(' ^ ')

    def visitBreak(self, node):
        # Break attributes
        #     None
        self.write('break ')
        self.NEWLINE()

    def visitCallFunc(self, node):
        # CallFunc attributes
        #     node             expression for the callee
        #     args             a list of arguments
        #     star_args        the extended *-arg value
        #     dstar_args       the extended **-arg value
        self.v(node.node)
        self.write('(')
        for i in range(len(node.args)):
            self.v(node.args[i])
            if i < (len(node.args) - 1):
                self.write(', ')
        if node.star_args:
            if len(node.args):
                self.write(', ')
            self.write('*')
            self.v(node.star_args)
        if node.dstar_args:
            if node.args or node.star_args:
                self.write(', ')
            self.write('**')
            self.v(node.dstar_args)
        self.write(')')

    def visitClass(self, node):
        # Class attributes
        #     name             the name of the class, a string
        #     bases            a list of base classes
        #     doc              doc string, a string or <code>None</code>
        #     code             the body of the class statement
        self.write('class %s' % node.name)
        if node.bases: self.write('(')
        else: self.write(':')
        for i in range(len(node.bases)):
            self.v(node.bases[i])
            if i < len(node.bases) - 1:
                self.write(',')
            else:
                self.write('):')
        self.INDENT()
        if node.doc:
            self.writestring(node.doc)
            self.NEWLINE()
        self.v(node.code)
        self.DEDENT()

    def visitComment(self, node):
        # Compare attributes
        #     value             
        self.write(node.value)
        self.NEWLINE()

    def visitCompare(self, node):
        # Compare attributes
        #     expr             
        #     ops              
        self.v(node.expr)
        for operator, operand in node.ops:
            self.write(' %s ' % operator)
            self.v(operand)

    def visitConst(self, node):
        # Const attributes
        #     value
        # i think !c@o#m$m%e^n&t* is an unfinished attempt to
        # save comments, which are normally stripped by parser...
        if isinstance(node.value, str) and \
           node.value.startswith('!c@o#m$m%e^n&t*'):
            self.write(node.value[15:])
        else:
            self.write(repr(node.value))

    def visitContinue(self, node):
        # Continue attributes
        #     None
        self.write('continue ')

    def visitDecorators(self, node):
        # Decorators attributes
        #     nodes            List of function decorator expressions
        raise NotImplementedException('visitDecorators')

    def visitDict(self, node):
        # Dict attributes
        #     items            
        self.write('{')
        for i in range(len(node.items)):
            k, v = node.items[i]
            self.v(k)
            self.write(': ')
            self.v(v)
            if i < len(node.items) - 1:
                self.write(' , ')
        self.write('} ')

    def visitDiscard(self, node):
        # Discard attributes
        #     expr
        self.v(node.expr)
        self.NEWLINE()

    def visitDiv(self, node):
        # Div attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' / ')
        self.v(node.right)

    def visitEllipsis(self, node):
        # Ellipsis attributes
        raise NotImplementedException('visitEllipsis')

    def visitExec(self, node):
        # Exec attributes
        #     expr             
        #     locals           
        #     globals          
        self.write('exec ')
        self.v(node.expr)
        if node.globals and node.locals:
            self.write(' in ')
            self.v(node.globals)
            self.write(', ')
            self.v(node.locals)
        elif node.globals:
            self.write(' in ')
            self.v(node.globals)
        elif node.locals:
            self.write(' in ')
            self.v(node.locals)
        self.NEWLINE()

    def visitFloorDiv(self, node):
        # FloorDiv attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' // ')
        self.v(node.right)      

    def visitFor(self, node):
        # For attributes
        #     assign           
        #     list             
        #     body             
        #     else_            
        self.write('for ')
        self.v(node.assign)
        self.write(' in ')
        self.v(node.list)
        self.write(':')
        self.INDENT()
        self.v(node.body)
        self.DEDENT()
        if node.else_:
            self.write('else:')
            self.INDENT()
            self.v(node.else_)
            self.DEDENT()

    def visitFrom(self, node):
        # From attributes
        #     modname          
        #     names            
        self.write('from %s import ' % node.modname)
        for i in range(len(node.names)):
            name, alias = node.names[i]
            self.write(name)
            if alias:
                self.write(' as %s' % alias)
            if i < len(node.names) - 1:
                self.write(', ')
        self.NEWLINE()

    def visitFunction(self, node):
        # Function attributes
        #     decorators       Decorators
        #     name             name used in def, a string
        #     argnames         list of argument names, as strings
        #     defaults         list of default values
        #     flags            xxx
        #     doc              doc string, a string or None
        #     code             the body of the function
        if node.decorators:
            for d in node.decorators:
                self.write('@')
                self.v(d)
                self.NEWLINE()
        hasvar = haskw = hasone = hasboth = False
        ndefaults = len(node.defaults)
        if node.flags & CO_VARARGS:
            hasone = hasvar = True
        if node.flags & CO_VARKEYWORDS:
            hasone = haskw = True
        hasboth = hasvar and haskw
        kwarg = None
        vararg = None
        defargs = []
        newargs = node.argnames[:]
        if haskw:
            kwarg = '**%s' % newargs.pop()
        if hasvar:
            vararg = '*%s' % newargs.pop()
        if ndefaults:
            for i in range(ndefaults):
                defargs.append((newargs.pop(), node.defaults.pop()))
            defargs.reverse()
        self.NEWLINE()
        self.write('def %s(' % node.name)
        for i in range(len(newargs)):
            if isinstance(newargs[i], tuple):
                self.write('(%s)' % ', '.join(newargs[i]))
            else:
                self.write(newargs[i])
            if i < len(newargs) - 1:
                self.write(', ')
        if defargs and len(newargs):
            self.write(', ')
        for i in range(len(defargs)):
            name, default = defargs[i]
            self.write('%s=' % name)
            self.v(default)
            if i < len(defargs) - 1:
                self.write(', ')
        if vararg:
            if (newargs or defargs):
                self.write(', ')
            self.write(vararg)
        if kwarg:
            if newargs or defargs or vararg:
                self.write(', ')
            self.write(kwarg)
        self.write('):')
        self.INDENT()
        if node.doc:
            self.writestring(node.doc)
            self.NEWLINE()
        self.v(node.code)
        self.DEDENT()

    def visitGenExpr(self, node):
        # GenExpr attributes   
        #     code             
        #     argnames, varargs, kwargs
        self.v(node.code)
    
    def visitGenExprInner(self, node):
        # GenExprInner attributes
        #     expr
        #     quals
        self.write('(')
        self.v(node.expr)
        for qual in node.quals:
            self.write(' for ')
            self.v(qual)
        self.write(')')

    def visitGenExprFor(self, node):
        # GenExprFor attributes
        #     assign           
        #     iter             
        #     ifs
        #     is_outmost
        self.v(node.assign)
        self.write(' in ')
        self.v(node.iter)
        for if_ in node.ifs:
            self.v(if_)

    def visitGenExprIf(self, node):
        # GenExprIf attributes 
        #     test             
        self.write(' if ')
        self.v(node.test)

    def visitGetattr(self, node):
        # Getattr attributes
        #     expr             
        #     attrname         
        self.v(node.expr)
        self.write('.%s' % node.attrname)

    def visitGlobal(self, node):
        # Global attributes
        #     names            
        self.write('global %s' % ', '.join(node.names))
        self.NEWLINE()

    def visitIf(self, node):
        # If attributes
        #     tests            
        #     else_
        el = ''
        for c, b in node.tests:
            self.write(el + 'if ')
            el = 'el'
            self.v(c)
            self.write(':')
            self.INDENT()
            self.v(b)
            self.DEDENT()
        if node.else_:
            self.write('else:')
            self.INDENT()
            self.v(node.else_)
            self.DEDENT()

    def visitIfExp(self, node):
        # IfExp attributes
        #     test
        #     then
        #     else_
        self.v(node.then)
        self.write(' if ')
        self.v(node.test)
        self.write(' else ')
        self.v(node.else_)

    def visitImport(self, node):
        # Import attributes
        #     names            
        self.write('import ')
        for i in range(len(node.names)):
            name, alias = node.names[i]
            self.write(name)
            if alias:
                self.write(' as %s' % alias)
            if i < len(node.names) - 1:
                self.write(', ')
        self.NEWLINE()

    def visitInvert(self, node):
        # Invert attributes
        #     expr             
        self.write('~')
        self.v(node.expr)

    def visitKeyword(self, node):
        # Keyword attributes
        #     name             
        #     expr             
        self.write(node.name)
        self.write('=')
        self.v(node.expr)

    def visitLambda(self, node):
        # Lambda attributes
        #     argnames         
        #     defaults         
        #     flags            
        #     code             
        hasvar = haskw = hasone = hasboth = False
        ndefaults = len(node.defaults)
        if node.flags & CO_VARARGS:
            hasone = hasvar = True
        if node.flags & CO_VARKEYWORDS:
            hasone = haskw = True
        hasboth = hasvar and haskw
        kwarg = None
        vararg = None
        defargs = []
        newargs = node.argnames[:]
        if haskw:
            kwarg = '**%s' % newargs.pop()

        if hasvar:
            vararg = '*%s' % newargs.pop()           
        if ndefaults:
            for i in range(ndefaults):
                defargs.append((newargs.pop(), node.defaults.pop()))
            defargs.reverse()       
        self.write('lambda ')
        for i in range(len(newargs)):
            if isinstance(newargs[i], tuple):
                self.write('(%s)' % ', '.join(newargs[i]))
            else:
                self.write(newargs[i])
            if i < len(newargs) - 1:
                self.write(', ')
        if defargs and len(newargs):
            self.write(', ')
        for i in range(len(defargs)):
            name, default = defargs[i]
            self.write('%s=' % name)
            self.v(default)
            if i < len(defargs) - 1:
                self.write(', ')
        if vararg:
            if (newargs or defargs):
                self.write(', ')
            self.write(vararg)
        if kwarg:
            if (newargs or defargs or vararg):
                self.write(', ')
            self.write(kwarg)
        self.write(' : ')
        self.v(node.code)


    def visitLeftShift(self, node):
        # LeftShift attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' >> ')
        self.v(node.right)

    def visitList(self, node):
        # List attributes
        #     nodes            
        self.write('[')
        for i in range(len(node.nodes)):
            self.v(node.nodes[i])
            if i < len(node.nodes) - 1:
                self.write(', ')
        self.write(']')

    def visitListComp(self, node):
        # ListComp attributes
        #     expr             
        #     quals            
        self.write('[')
        self.v(node.expr)
        for qual in node.quals:
            self.write(' for ')
            self.v(qual)
        self.write(']')

    def visitListCompFor(self, node):
        # ListCompFor attributes
        #     assign           
        #     list             
        #     ifs              
        self.v(node.assign)
        self.write(' in ')
        self.v(node.list)
        for if_ in node.ifs:
            self.v(if_)

    def visitListCompIf(self, node):
        # ListCompIf attributes
        #     test             
        self.write(' if ')
        self.v(node.test)

    def visitMod(self, node):
        # Mod attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' % ')
        self.v(node.right)      

    def visitModule(self, node):
        # Module attributes
        #     doc              doc string, a string or None
        #     node             body of the module, a Stmt
        if node.doc:
            self.writestring(node.doc)
            self.NEWLINE()
        self.v(node.node)

    def visitMul(self, node):
        # Mul attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' * ')
        self.v(node.right)

    def visitName(self, node):
        # Name attributes
        #     name             
        self.write(node.name)

    def visitNot(self, node):
        # Not attributes
        #     expr             
        self.write(' not ')
        self.v(node.expr)

    def visitOr(self, node):
        # Or attributes
        #     nodes            
        for n in node.nodes[:-1]:
            self.v(n)
            self.write(' or ')
        self.v(node.nodes[-1])

    def visitPass(self, node):
        # Pass attributes
        #     None
        self.write('pass ')
        self.NEWLINE()

    def visitPower(self, node):
        # Power attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' ** ')
        self.v(node.right)      

    def visitPrint(self, node):
        # Print attributes
        #     nodes            
        #     dest             
        self.write('print ')
        nnodes = len(node.nodes)
        if node.dest:
            self.write('>> ' )
            self.v(node.dest)
            if nnodes:
                self.write(', ')
        for i in range(nnodes):
            n = node.nodes[i]
            self.v(n)
            self.write(', ')
        self.NEWLINE()

    def visitPrintnl(self, node):
        # Printnl attributes
        #     nodes            
        #     dest
        self.write('print ')
        nnodes = len(node.nodes)
        if node.dest:
            self.write('>> ' )
            self.v(node.dest)
            if nnodes:
                self.write(', ')
        for i in range(nnodes):
            n = node.nodes[i]
            self.v(n)
            if i < nnodes - 1:
                self.write(', ')
        self.NEWLINE()

    def visitRaise(self, node):
        # Raise attributes
        #     expr1            
        #     expr2            
        #     expr3            
        self.write('raise ')
        if node.expr1:
            self.v(node.expr1)
        if node.expr2:
            self.write(', ')
            self.v(node.expr2)
        if node.expr3:
            self.write(', ')
            self.v(node.expr3)
        self.NEWLINE()

    def visitReturn(self, node):
        # Return attributes
        #     value            
        self.write('return ')
        self.v(node.value)

    def visitRightShift(self, node):
        # RightShift attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' >> ')
        self.v(node.right)

    def visitSlice(self, node):
        # Slice attributes
        #     expr             
        #     flags            
        #     lower            
        #     upper            
        if node.flags == OP_DELETE:
            self.write('del ')
        self.v(node.expr)
        self.write('[')
        if node.lower:
            self.v(node.lower)
        self.write(':')
        if node.upper:
            self.v(node.upper)
        self.write(']')
        if node.flags == OP_DELETE:
            self.NEWLINE()

    def visitSliceobj(self, node):
        # Sliceobj attributes
        #     nodes            list of statements
        #self.write('[')
        if not hasattr(node.nodes[0], 'value') or node.nodes[0].value:
            self.v(node.nodes[0])   # avoid writing 'None' for missing parts
        self.write(':')
        if not hasattr(node.nodes[1], 'value') or node.nodes[1].value:
            self.v(node.nodes[1])
        if not hasattr(node.nodes[2], 'value') or node.nodes[2].value:
            self.write(':')
            self.v(node.nodes[2])
        #self.write(']')

    def visitStmt(self, node):
        # Stmt attributes
        #     nodes
        for n in node.nodes:
            self.v(n)

    def visitSub(self, node):
        # Sub attributes
        #     left             
        #     right            
        self.v(node.left)
        self.write(' - ')
        self.v(node.right)

    def visitSubscript(self, node):
        # Subscript attributes
        #     expr             
        #     flags            
        #     subs             
        if node.flags == OP_DELETE:
            self.write('del ')
        self.v(node.expr)
        self.write('[')
        for i in range(len(node.subs)):
            self.v(node.subs[i])
            if i == len(node.subs) - 1:
                self.write(']')
        if node.flags == OP_DELETE:
            self.NEWLINE()

    def visitTryExcept(self, node):
        # TryExcept attributes
        #     body             
        #     handlers         
        #     else_            
        self.write('try:')
        self.visitBlock(node.body)
        for h in node.handlers:
            self.write('except')
            expr, target, body = h
            if expr:
                self.write(' ')
                self.v(expr)
            if target:
                self.write(', ')
                self.v(target)
            self.write(':')
            self.visitBlock(body)
        if node.else_:
            self.write('else:')
            self.INDENT()
            self.v(node.else_)
            self.DEDENT()
        self.NEWLINE()

    def visitTryFinally(self, node):
        # TryFinally attributes
        #     body             
        #     final            
        self.write('try:')
        self.INDENT()
        self.v(node.body)
        self.DEDENT()
        self.write('finally:')
        self.INDENT()
        self.v(node.final)
        self.DEDENT()

    def visitTuple(self, node):
        # Tuple attributes
        #     nodes            
        self.write('(')
        if node.nodes:
            for i in range(len(node.nodes) - 1):
                self.v(node.nodes[i])
                self.write(', ')
            self.v(node.nodes[-1])
            if len(node.nodes) == 1:
                self.write(',')
        self.write(')')

    def visitUnaryAdd(self, node):
        # UnaryAdd attributes
        #     expr             
        self.write('+')
        self.v(node.expr)

    def visitUnarySub(self, node):
        # UnarySub attributes
        #     expr             
        self.write('-')
        self.v(node.expr)

    def visitWhile(self, node):
        # While attributes
        #     test             
        #     body             
        #     else_            
        self.write('while ')
        self.v(node.test)
        self.write(':')
        self.INDENT()
        self.v(node.body)
        if node.else_:
            self.DEDENT()
            self.write('else:')
            self.INDENT()
            self.v(node.else_)
        self.DEDENT()

    def visitWith(self, node):
        # With attributes
        #     expr             
        #     vars             
        #     body
        # NOTE: must be changed to support Python 2.7, as
        #       it allows multiple context expressions
        self.write('with ')
        self.v(node.expr)
        if node.vars:
            self.write(' as ')
            self.v(node.vars)
        self.write(':')
        self.INDENT()
        self.v(node.body)
        self.DEDENT()
        
    def visitYield(self, node):
        # Yield attributes
        #     value            
        self.write('yield ')
        self.v(node.value)
        self.NEWLINE()



def ast2py(ast, comments, stream=None):
    if stream is None:
        stream = file('output.py', 'w')
    v = UnparsingVisitor(stream, comments)
    v.v(ast)
    try:
        stream.close()
    except:
        pass


def get_comments(f):
    import token
    from tokenize import generate_tokens
    comments = {}
    for t in generate_tokens(file(f).readline):
        if t[0] == token.N_TOKENS:  # comment
            if t[4].lstrip().startswith(t[1]):
                type = 'standalone'
            else:
                type = 'inline'
            comments[t[2][0]] = (t[1], type)
    return comments


def parse_with_comments(f):
    ast = parse(file(f).read())
    comments = get_comments(f)
    return ast, comments


def print_code_and_ast(f, ast, comments):
    from pprint_ast import pprintAst, dump
    from StringIO import StringIO
    if f == 'parser_test_source.py':
        s = StringIO()
        #pprintAst2(ast, stream=sys.stdout);print;print
        #pprintAst(ast, stream=s)
        dump(ast)
        '''
        t = file(f).readlines()
        for i, line in enumerate(t):
            print line.strip('\n').ljust(60),
            s.seek(0)
            for n in s.readlines():
                if n[:n.find(':')] == str(i + 1):
                    print n.strip('\n'),
                    break
            print
        '''

def test(modules=None):
    import os
    import ast as ast_mod
    if not modules:
        #d = 'C:\\Python25\\Lib\\'
        d = '/usr/lib/python2.7/'
        modules = [d + f for f in os.listdir(d) if f.endswith('.py')]
    for f in modules:
        shutil.copy(f, 'input.py')
        msg = '%s...' % os.path.basename(f)
        ast, comments = parse_with_comments(f)
        print_code_and_ast(f, ast, comments)
        print
        print
        print ast_mod.dump(ast_mod.parse(file(f).read()), 0)
        try:
            ast2py(ast, comments)
        except:
            raise
            msg += 'failed to converting AST back to python code'
        try:
            if f == 'parser_test_source.py':
                print;print
                print file('output.py').read()   # see the results
            parse(file('output.py').read())
            msg += 'OK'
        except:
            raise
            msg += 'failed to parse generated code'
        print msg

        break





if __name__ == '__main__':
    f = 'parser_test_source.py'
    #f = 'C:\\Python25\\Lib\\smtpd.py'
    #f = '/usr/lib/python2.6/difflib.py'

    test()
    #test([f])




'''

TODO:

  NOT IMPLEMENTED YET:
    (*) decorators

  ERRORS:

    (*) parens are not preserved when used for precedence altering in
        expressions - i either have to add parens around everything or worse
        (and currently) strip them all


  ISSUES:
    (*) long lines should wrap after 80 chars
    (*) puts extra newlines - better than too few and could reduce in
        post-processing step, but more complex control requires inline handling
    (*) compiler.parse strips comments
    (*) generator expressions add unneeded parens if inside function call



perhaps it would make sense to convert AST to a custom data structure, fixing
any peculiarities prior to any complex manipulations..

how about xml, so advanced features like xpath can be used?



'''









