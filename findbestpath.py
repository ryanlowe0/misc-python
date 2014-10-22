#!/usr/bin/env python 

import sys

if sys.argv[1] == '1':
    f = 'triangle.txt'
else:
    f = 'trimini.txt'

tree = []
for line in file(f):
    tree.append(map(int, line.strip().split(' ')))

height = len(tree)
width = len(tree[-1])
if f == 'trimini.txt':
    for i, row in enumerate(tree):
        print ' ' * (height - i), ' '.join(map(str, row))
    print 

print tree

'''
mat = [[()] * width for i in range(height)]
mat[-1] = zip(tree[-1][:], range(width))
for level in range(height - 2, -1, -1):
    row = tree[level]
    #print 'row', row
    mat[level][0] = row[0], 0
    mat[level][-1] = row[-1], len(row) - 1
    pre = None
    for col in range(1, width - 1):
        cur = mat[level + 1][col]
        #print cur,
        if cur == pre:
            mat[level][col] = mat[level][col - 1]
            #print 'rep', mat[level][col - 1]
        else:
            if cur[1] < 1:
                #print 'lo', row[0]
                mat[level][col] = row[0], 0
            elif cur[1] > len(row) - 1:
                #print 'lo', row[0]
                mat[level][col] = row[-1], len(row) - 1
            else:
                left = row[cur[1] - 1]
                right = row[cur[1]]
                if left > right:
                    #print 'left', left
                    mat[level][col] = left, cur[1] - 1
                else:
                    #print 'right', right
                    mat[level][col] = right, cur[1]
        pre = cur
    #print

sums = [0] * width
paths = [[] for x in range(width)]
for j, row in enumerate(mat):
    for i, x in enumerate(row):
        sums[i] += x[0]
        paths[i].append(x[1])
print sums
m = max(sums)
i = sums.index(m)
print m, i
print paths[i]
print sum(tree[row][paths[i][row]] for row in range(height))

print;print
best_sum = 0
best_path = []
tried = 0
def bfs(v, s, p):
    global best_sum, best_path, tried
    row, col = v
    s += tree[row][col]
    p.append(col)
    if row < height - 1:
        left = [row + 1, col]
        right = [row + 1, col + 1]
        ledge, redge = tuple(v + left), tuple(v + right)
        bfs(left, s, p[:])
        if col + 1 < len(tree[row]):
            bfs(right, s, p[:])
    else:
        tried += 1
        if s > best_sum:
            print '%s(%s)' % (s, tried),
            best_sum = s
            best_path = p[:]

bfs([0, 0], 0, [])
print;print
print tried
print best_sum
print best_path

'''

from copy import deepcopy
sums = [(tree[-1][i], [i]) for i in range(width)]
print sums
for level in range(height - 2, -1, -1):
    row = tree[level]
    new_sums = row[:]
    #print level,
    for c in range(len(row)):
        a, ap = sums[c]
        b, bp = sums[c + 1]
        if a > b:
            new_sums[c] = a + row[c], [c] + ap[:]
        else:
            new_sums[c] = b + row[c], [c] + bp[:]
            
    sums = deepcopy(new_sums)
    #print sums

print sums[0][0]
print sums[0][1]
print sum(tree[i][sums[0][1][i]] for i in range(height))



