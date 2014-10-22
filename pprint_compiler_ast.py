## {{{ http://code.activestate.com/recipes/533145/ (r1)
"""Python AST pretty-printer.

To me, it is totally unf*ckinbelievable that the standard Python compiler module
does not come with a pretty-printer for the AST. Here is one.
"""

import sys
#from compiler.ast import Node
from ast import AST as Node


def pprintAst(ast, indent='  ', stream=sys.stdout):
    "Pretty-print an AST to the given output stream."
    rec_node(ast, 0, indent, stream.write, 1)

def dump(node, write=sys.stdout.write):
    if isinstance(node, Node):
        write(node.__class__.__name__ + '(')
        if any(isinstance(child, Node) for child in node.getChildren()):
            for i, child in enumerate(node.getChildren()):
                if i != 0: write(', ')
                dump(child)
        else:
            write(', '.join(repr(child) for child in node.getChildren()))
        write(')')
    else:
        write(repr(node))


def rec_node(node, level, indent, write, lineno):
    "Recurse through a node, pretty-printing it."
    pfx = indent * level
    if isinstance(node, Node):
        '''
        p = pfx
        if node.lineno:
            ln = '%s:' % node.lineno
            write(ln)
            p = p[:-len(ln)]
            write(p)
        else:
            write(pfx)
        '''
        write(node.__class__.__name__)
        print dir(node)
        attrs = [x for x in dir(node) if not x[0] == '_' and x not in
                 ('asList', 'getChildNodes', 'getChildren', 'lineno')]
        #write('(%s) ' % ', '.join(attrs))
        write('(')

        if any(isinstance(child, Node) for child in node.getChildren()):
            for i, child in enumerate(node.getChildren()):
                if i != 0:
                    write(',')
                if getattr(child, 'lineno', 0) > lineno:
                    lineno = child.lineno
                    write('\n%s:%s' % (lineno, pfx))
                rec_node(child, level+1, indent, write, lineno)
            #write('\n')
            #write(pfx)
        else:
            # None of the children as nodes, simply join their repr on a single
            # line.
            write(', '.join(repr(child) for child in node.getChildren()))

        write(')')

    else:
        #write(pfx)
        write(repr(node))


if __name__ == '__main__':
    def test():
        import compiler
        pprintAst(compiler.parseFile(__file__))
    test()
## end of http://code.activestate.com/recipes/533145/ }}}


'''



Can the pretty printer be made to show the tags on their original line, with
the code next to it?

Can the output visitor be made to respect line boundaries from the original,
only adjusting spaces and parens essentially?

In addition to my attempts to simplify the ast into a basic data structure, I
may also want to think about extending it with various meta data, like local
variable tracking, etc

The trick is how to be simultaneously aware of the the look of the code
(syntax) and the tree structure of the ast (semantics..sort of)

'''
