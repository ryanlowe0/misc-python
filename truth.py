#!/usr/bin/env python


from tools import *

def logic(s, trace=0):
    def imp(p, q): 
        return not p or q
    def eq(p, q): return not p and not q or p and q
    class _:
        def __init__(self, val): self.val = bool(val)
        def __str__(self): return str(self.val).lower()
        def __gt__(self, x): return _(imp(self.val, _(x)))
        def __ne__(self, x): return _(eq(self.val, _(x)))
        def __invert__(self): return _(not self.val)
        def __trunc__(self): return self.val.__trunc__()
        def __nonzero__(self): return self.val.__nonzero__()
    print lightyellow(str(s).ljust(35)),
    vars_ = list(set(re.findall('\w+', s)) - set(['A', 'V']))
    if len(vars_) > 3:
        raise ValueError('Only formulas with 3 or fewer variables allowed')
    for v1, v2 in zip(['p', 'q', 'r'], vars_):
        s = s.replace(v2, v1)
    #s = s.replace('a', 'p').replace('b', 'q').replace('c', 'r')
    has_p = 'p' in s
    has_q = 'q' in s
    has_r = 'r' in s
    s = s.replace('<=>', '<>').replace('=>', '>')
    s = s.replace('p', '_(p)').replace('q', '_(q)').replace('r', '_(r)')
    s = s.replace('V', ' or ').replace('A', ' and ')
    #print lightmagenta(s)
    ans = []
    for p, q, r in [(p, q, r) for p in (False, True) for q in (False, True) for
                    r in (False, True)]:
        if not has_p and not p:
            continue
        if not has_q and not q:
            continue
        if not has_r and not r:
            continue
        p, q, r = map(_, (p, q, r))
        x = eval(s)
        P, Q, R = str(p)[0].upper(), str(q)[0].upper(), str(r)[0].upper()
        if not has_p: P = '-'
        if not has_q: Q = '-'
        if not has_r: R = '-'
        #print P + Q + R, lightgreen(x) if x else lightred(x)
        ans.append(x)
        if trace: 
            print 'p =', p, 'q =', q, 'r =', r
            print lightgreen(str(x).rjust(5)) if x else lightred(str(x).rjust(5))
    if trace: print
    sat = ['pqr=' + str(bin(i))[2:].zfill(3) for i, v in enumerate(ans)
           if eval(str(v).title())]
    if len(sat) == len(ans):
        print 'Valid'
    elif not sat:
        print 'Unsatisfiable'
    else:
        print 'Invalid but Satisfiable'
    return sat

logic('p => q')
logic('a <=> b')

logic('a A b A c')
logic('a => b')
logic('b => c')
logic('c => a')
logic('(a => b) A (b => c)')
logic('(b => c) A (c => a)')
logic('(a => b) A (b => c) A (c => a)')
print
logic('(a => c) A (b V ~b)')
logic('((a => b) A (b => c)) <=> (a => c)')
print

logic('(p => q) <=> (p V ~q)')
logic('(p => q) <=> (~q => ~p)')
logic('p V q V (p => q)')
logic('p A q <=> ~(~p V ~q)')


logic('~a')
logic('a V ~a')
logic('(a A ~a) => (b => c)')
logic('(a => b) A (b => c) A (c => a)')
logic('(a => b) A ~(~a V b)')
logic('((a => b) A (b => c)) <=> (a => c)')

#print logic('(p V r) A (p A (q V ~r)) A (~q V ~r) A (~p V ~q)', 0)
#print logic('(p V q V r) A (~p V ~(q V r)) A (~q V ~(p V r))', 0)
print logic('(statue A ~pupil => creepy) <=> (statue A pupil => ~creepy)') 
print

#A = 'p'
#B = 'p V q'
#C = 'p A q'
#D = '~p => q'

#q = 'A B C D'
#print '      ', lightyellow(q)
#print '     +--------'
#for x in q.split(' '):
#    print lightyellow(x), '=> |',
#    for y in q.split(' '):
#        s = '(%s) => (%s)' % (eval(x), eval(y))

#        print lightgreen('T') if all(logic(s, 0)) else '.',
#    print
