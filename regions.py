#!/usr/bin/env python


# relations of region b
# b                 = (s, e, s, e) 
# before b          = (0, 0, s, s)
# overlaps-start b  = (0, s, s, e) 
# contains b        = (0, e, s, N)
# after b           = (e, e, N, N) 
# overlaps-end b    = (s, e, e, N) 
# in b              = (s, s, e, e)

# relations of region rectangle B
# B                 = (s1, e1, s2, e2) 
# before B          = ( 0,  0, s2, s2)
# overlaps-start B  = ( 0, s1, s2, e2) 
# contains B        = ( 0, e1, s2,  N)
# after B           = (e1, e1,  N,  N) 
# overlaps-end B    = (s1, e1, e2,  N)
# in B              = (s1, s1, e2, e2)

# union, intersection, difference
