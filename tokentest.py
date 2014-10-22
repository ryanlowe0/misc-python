




from tokenize import *

def tokenPrinter(source, lineno=False):
    comments = {}
    indent = ''
    nl = 0
    i = 1
    lines = len(file(source).readlines())
    print str(i).rjust(len(str(lines))),
    for t in generate_tokens(file(source).readline):
        if t[0] in (NL, NEWLINE):
            i += 1
            print
            if lineno:
                print str(i).rjust(len(str(lines))),
            nl = 1
        elif t[0] == INDENT:
            indent = t[1]
        elif t[0] == DEDENT:
            indent = indent[:-4]
        else:
            if nl:
                if indent:
                    print indent,
                nl = 0
            if t[0] in (NAME, STRING, NUMBER):
                print t[1],
            elif t[0] == OP:
                print '%s(%s)' % (tok_name[t[0]], t[1]),
            elif t[0] == NUMBER:
                print 'NUM_%s' % t[1],
            else:
                print '%s(%s)' % (tok_name[t[0]], t[1]),
                #print '%s' % t[1],
        if t[0] == COMMENT:  # comment
            txt = ' ' * t[2][1] + t[1]
            standalone = t[4].strip().startswith(t[1].strip())
            comments[t[2][0]] = (txt, standalone)
    return comments




tokenPrinter('parser_test_source.py', 1)

print;print

for t in generate_tokens(file('parser_test_source.py').readline):
    print t




