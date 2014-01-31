#!/usr/bin/env python


'''

An interpreter for the Joy programming language written in Python.

'''


from tools import *
from copy import deepcopy


ALIASES = {
    '+': 'add', 'cat': 'add', 'concat': 'add',
    '-': 'sub',
    '*': 'mul',
    '/': 'div',
    '^': 'pow_',
    '<': 'lt',
    '<=': 'le',
    '>': 'gt',
    '>=': 'ge',
    '=': 'eq',
    '!=': 'ne', '<>': 'ne',
    '%': 'mod', 'rem': 'mod',
    '++': 'succ',
    '--': 'pred',
    'reduce': 'fold',
    'len': 'size',
    'prepend': 'push',
    '..': 'range'
}


DEFINITIONS = {
    'factorial': '[null] [++] [dup -- factorial *] ifte'

}


class Joy(object):

    def __init__(self):
        self.aliases = ALIASES
        self.definitions = {}
        for k, v in DEFINITIONS.items():
            self.definitions[k] = self.parse(v)


    def addCommand(self, method, aliases=[]):
        'Add an externally defined method.'
        import new
        name = method.__name__
        for a in self.aliases: self.aliases[a] = name
        value = new.instancemethod(method, self, self.__class__)
        setattr(self, name, value)


    def tokenize(self, prog):
        from StringIO import StringIO
        from tokenize import generate_tokens
        import token
        tokens = []
        prev = [0, '', (), ()]
        for t in generate_tokens(StringIO(prog).readline):
            s = t[1].strip()
            if t[0] == token.NUMBER:
                if '.' in s:
                    tokens.append(float(s))
                else:
                    tokens.append(int(float(s)))
            elif (t[2] == prev[3] and t[0] != token.STRING and
                  s not in '[]' and prev[1] not in '[]' and tokens):
                tokens[-1] += s  # part of previous token
            elif s and t[0] not in (token.INDENT, token.DEDENT, 53):
                tokens.append(s)
            prev = t
        return tokens


    def quotify(self, tokens):
        'Turn token list into nested list. '
        res = []
        depth = 0
        for t in tokens:
            if t == '[':
                spot = res
                for d in range(depth): spot = spot[-1]
                spot.append([])
                depth += 1
            elif t == ']':
                depth -= 1
            else:
                spot = res
                for d in range(depth): spot = spot[-1]    
                spot.append(t)
        return res
    

    def parse(self, prog):
        tokens = self.tokenize(prog.strip())
        import keyword
        # map tokens to method names
        for i, t in enumerate(tokens):
            if t in self.aliases: t = self.aliases[t]
            if t in keyword.kwlist + dir(__builtins__): t += '_'
            tokens[i] = t
        #print ' '.join([str(t).rstrip('_') for t in tokens])
        tokens = self.quotify(tokens)
        return tokens

    
    def run(self, prog):
        tokens = self.parse(prog)
        self.global_stack = []
        res = self.eval(tokens, [])
        return ' '.join(map(str, reversed(res)))
    
    def stack_str(self, stack):
        return ' '.join([str(t).rstrip('_') for t in stack])

    def eval(self, tokens, stack, level=0):
        line = 1
        while tokens:
            gs = self.stack_str(self.global_stack)
            ls = self.stack_str(stack)
            tok = tokens.pop(0)
            print '\t' * level + lightyellow(tok), gs.replace(ls, lightblue(ls))
            if level == 0:
                self.global_stack = stack[:]
            if tok == '\n': line += 1
            elif isinstance(tok, list):
                stack.insert(0, tok)
            elif tok in self.definitions:
                self.eval(deepcopy(self.definitions[tok]), stack, level+1)
            elif str(tok).startswith('py:'):
                self.doPy(tok.split(':')[1], stack)
            elif tok not in dir(self):
                stack.insert(0, tok)
            else:
                #print lightyellow(stack)
                getattr(self, tok)(stack)
            gs = self.stack_str(self.global_stack)
            ls = self.stack_str(stack)
            print gs.replace(ls, lightblue(ls))
            if level == 0:
                self.global_stack = stack[:]
            print '---'
        return stack

    def doPy(self, tok, stack):
        parts = tok.split('.')
        cnt = stack.pop(0)
        args = stack[:cnt]
        if len(parts) > 1:
            tok = '__import__(parts[0]).%s' % '.'.join(parts[1:])
        stack[:cnt] = [eval(tok)(*args)]
        
                    

    def add(self, stack): stack[:2] = [stack[1] + stack[0]]
    def sub(self, stack): stack[:2] = [stack[1] - stack[0]]
    def neg(self, stack): stack[0] = -stack[0]
    def mul(self, stack): stack[:2] = [stack[1] * stack[0]]
    def div(self, stack): stack[:2] = [stack[1] / stack[0]]
    def pow_(self, stack): stack[:2] = [stack[1] ** stack[0]]
    def lt(self, stack): stack[:2] = [stack[1] < stack[0]]
    def le(self, stack): stack[:2] = [stack[1] <= stack[0]]
    def gt(self, stack): stack[:2] = [stack[1] > stack[0]]
    def ge(self, stack): stack[:2] = [stack[1] >= stack[0]]
    def eq(self, stack): stack[:2] = [stack[1] == stack[0]]
    def ne(self, stack): stack[:2] = [stack[1] != stack[0]]
    def mod(self, stack): stack[:2] = [stack[1] % stack[0]]
    def and_(self, stack): stack[:2] = [stack[1] and stack[0]]
    def or_(self, stack): stack[:2] = [stack[1] or stack[0]]
    def xor(self, stack): stack[:2] = [stack[1] ^ stack[0]]
    def not_(self, stack): stack[0] = not stack[0]
    def succ(self, stack): stack[0] += 1
    def pred(self, stack): stack[0] -= 1
    def true(self, stack): stack.insert(0, True)
    def false(self, stack): stack.insert(0, False)
    def null(self, stack): stack[0] = not bool(stack[0])
    def pop(self, stack): stack.pop(0)
    def dup(self, stack): stack.insert(0, deepcopy(stack[0]))
    def swap(self, stack): stack[0], stack[1] = stack[1], stack[0]
    def first(self, stack): stack[:1] = stack[:1][0]
    def last(self, stack): stack[:1] = stack[:1][-1]
    def rest(self, stack): stack[:1] = stack[:1][1:]
    def at(self, stack): stack[:2] = [stack[1][stack[0]]]
    def of(self, stack): stack[:2] = [stack[0][stack[1]]]
    def size(self, stack): stack[0] = len(stack[0])
    def i(self, stack): stack[:1] = stack[0]
    def min_(self, stack): stack[0] = min(stack[0])
    def max_(self, stack): stack[0] = max(stack[0])
    def sum_(self, stack): stack[0] = sum(stack[0])
    def abs_(self, stack): stack[0] = abs(stack[0])
    def sign(self, stack): stack[0] = cmp(stack[0], 0)
    def drop(self, stack): stack[:2] = stack[0][stack[1]:]
    def take(self, stack): stack[:2] = stack[0][:stack[1]]
    def odd(self, stack): stack[0] = stack[0] % 2 != 0
    def even(self, stack): stack[0] = stack[0] % 2 == 0
    def pos(self, stack): stack[0] = stack[0] > 0
    def neg(self, stack): stack[0] = stack[0] < 0
    def in_(self, stack): stack[:2] = stack[1] in stack[0]
    def has(self, stack): stack[:2] = stack[0] in stack[1]
    def reverse(self, stack): stack[0] = reversed(stack[0])
    def append(self, stack): stack[:1] = stack[0] + [stack[1]]
    def push(self, stack): stack[:1] = [stack[0]] + stack[1]
    def range_(self, stack): stack[:2] = [range(stack[1], stack[0])]
    def put(self, stack): print eval(str(stack[0])),
    def write(self, stack): sys.stdout.write(eval(str(stack[0])))
    def stack(self, stack): stack.insert(0, deepcopy(stack))
    def clear(self, stack): stack[:] = []
    def print_(self, stack): print stack
    def dump(self, stack):
        print 'stack:',
        if len(stack) > 1: print
        for i, s in enumerate(stack):
            pre, post = ' ', ''
            if not i: pre = '['
            if i == len(stack) - 1: post = ']'
            print pre, s, post
        print
        stack[:] = []
    def nl(self, stack):
        print
    
    def map_(self, stack):
        prog, seq = deepcopy(stack[:2])
        for i, t in enumerate(seq): seq[i] = self.eval(deepcopy(prog), [t])[0]
        stack[:2] = [seq]
        
    def step(self, stack):
        prog, seq = deepcopy(stack[:2])
        del stack[:2]
        for t in seq: self.eval(deepcopy(prog), [t])
        
    def times(self, stack):
        prog, num = deepcopy(stack[:2])
        del stack[:2]
        for i in range(num): self.eval(deepcopy(prog), stack)
                    
    def fold(self, stack):
        prog, e, seq = deepcopy(stack[:3])
        del stack[:3]
        if not seq:
            stack.insert(0, e)
        else:
            while len(seq) > 1:
                s = [seq[1], seq[0]]
                seq[:2] = [self.eval(deepcopy(prog), s)[0]]
            stack.insert(0, seq[0])
            
    def filter_(self, stack):
        prog, seq = deepcopy(stack[:2])
        del stack[:2]
        seq2 = []
        for t in seq:
            if self.eval(deepcopy(prog), [t])[0]:
                seq2.append(t)
        stack.insert(0, seq2)

    def cleave(self, stack):
        '''Runs 2 diff quoted progs on seq in parallel,
           pushes both results.

            <seq> [prog1] [prog2] cleave'''
        prog1, prog2, top = deepcopy(stack[:3])
        del stack[:2]
        stack[:1] = [self.eval(prog1, deepcopy(stack))[0],
                     self.eval(prog2, deepcopy(stack))[0]]
        
    def dip(self, stack):
        prog, top = deepcopy(stack[:2])
        del stack[:2]
        self.eval(prog, stack)
        stack.insert(0, top)
        
    def cons(self, stack):
        top, next = deepcopy(stack[:2])
        del stack[:2]
        stack[:0] = [next] + self.eval(top, deepcopy(stack))[:1]
        
    def ifte(self, stack):
        e, t, i = deepcopy(stack[:3])
        del stack[:3]
        res = self.eval(i, deepcopy(stack))[0]
        if res: self.eval(t, stack)
        else: self.eval(e, stack)

    def while_(self, stack):
        prog, cond = deepcopy(stack[:2])
        del stack[:2]
        while self.eval(deepcopy(cond), deepcopy(stack))[0]:
            self.eval(deepcopy(prog), stack)

    def def_(self, stack):
        prog = stack.pop(0)
        name = prog.pop(0)
        # if prog is empty, use top of stack
        # this is essentially the same as variable binding
        if prog: self.definitions[name] = prog
        else:    self.definitions[name] = [stack.pop(0)]

    def undef(self, stack): del self.definitions[stack.pop(0)[0]]
        
    def nullary(self, stack):
        stack[:1] = self.eval(deepcopy(stack[0]), deepcopy(stack[1:]))
        
    def unary(self, stack):
        stack[:2] = self.eval(deepcopy(stack[0]), deepcopy(stack[1:]))
        
    def rollup(self, stack): stack[:3] = [stack[2], stack[0], stack[1]]
    def rolldown(self, stack): stack[:3] = [stack[1], stack[2], stack[0]]

    def unit(self, stack): stack[:1] = [stack[0]]



def test():
    joy = Joy()

    joy.run('''

        #[ popd  [pop ] dip ] def
        #[ dupd  [dup ] dip ] def
        #[ swapd [swap] dip ] def

       # 
        #1 2 3 swapd                                 dump
        #[1 2 3 4 5] [6 -] map                       dump
        #1 2 3 [pop] dip                             dump
        #[1 2 3 4] 2 at                              dump
        #2 [1 2 3 4] of                              dump
        12 [1000 <] [2 /] [3 *] ifte                dump
        #[1 2 3 4] [1 + put] step                    dump
        #[1 2 3 4] [3 <] filter                      dump
        #[2 5 3] 0 [+] fold                          dump
        #[2 5 3] 0 [dup * +] fold                    dump
        #[2 6 4] dup 0 [+] fold swap size /          dump
        #[2. 5 4] [0 [+] fold] [size] cleave /       dump
        #[1 2] len 2 =                               dump

        #9 
        #  [2 >] 
        #  [1 - put '::' write pop] 
        #while
        #pop
        #nl nl


        #[ lower 1 py:string.lower ] def
        #'ThIs HAd fUnkY CaSinG' lower               dump

       # 
        #[fact [1 1] dip [dup [*] dip succ] times pop] def
        #5 fact                                       dump
        

        #[ fib
        #        [1 0] dip
        #        [swap [+] unary]
        #    times
        #        [pop]
        #    dip
        #] def


        #8 fib dump

        #[dig2 [] cons cons dip] def
        #['C'] ['B'] ['A'] dig2 dump
       # 
        #1 9 .. dump


    ''')

    

if __name__ == '__main__':
    test()










                
