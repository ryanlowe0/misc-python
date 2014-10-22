#!/usr/local/bin/python

import re, pprint



def filter_list(regex, flist):
    ' Returns sublist that matches (or not if inverse flag ~) a regex '
    
    if regex[0] == '~':
        inverse = True
        regex = regex[1:]
    else:
        inverse = False
    
    # make sure it matches complete name
    if not regex.endswith('$'):
        regex += '$'
    rv = []
    for x in flist:
        if re.match(regex, x):
            if not inverse:
                rv.append(x)
        elif inverse:
            rv.append(x)
    return rv

    

class Tree(object):
    '''
    Tree objects provide:
    * Flexible access using dot.syntax, lookup['syntax'],
      or location[0] syntax
    * Regular expression matching of attributes
    * Data initialization upon first assingment or augmented assignment
    * Persistent (but modifiable) attribute ordering
    * Converting to and from nested list/tuple/dict structure
    * Filterable recursive function mapping to nodes


    data[:]         list of node refs
    data['.*']      same
    data.keys()     list of node names
    data.values()   list of node values
    
    problems:
    -cant delete because need to access parent's __keys
    -data[:] should return node refs

    '''
    
    def __init__(self, inobj=None):
        if not inobj:
            object.__setattr__(self, '_Tree__keys', [])

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            self.__setattr__(name, Tree())
            return object.__getattribute__(self, name)

    def __iadd__(self, item):
        self = item
        return self

    def __nonzero__(self):
        if self.__keys:
            return True
        return False

    def __len__(self):
        return len(self.__keys)

    def __str__(self):
        if not self.__keys:
            return 'nil'
        return ', '.join(self.__keys)

    def __call__(self, *args, **kwargs):
        return ''
        return self.__str__()

    def __iter__(self):
        for i in range(len(self.__keys)):
            yield self[i]
        
    def __setattr__(self, item, value):
        if item not in self.__keys:
            self.__keys.append(item)
        object.__setattr__(self, item, value)

    def __getitem__(self, item):
        rv = None
        if isinstance(item, int):
            try:
                rv = self.__getattribute__(self.__keys[item])
            except:
                pass
        elif isinstance(item, str):
            item = item.strip()     # ignore surrounding whitespace
            rv = self.keys(item)
            # only return a list if more than one item is found
            if len(rv) == 0:
                self.__setitem__(item, Tree())
                rv = self.__getattribute__(item)
            elif len(rv) == 1:
                rv = self.__getattribute__(rv[0])
            else:
                keys = rv
                rv = []
                for x in keys:
                    rv.append(self.__getattribute__(x))
        elif isinstance(item, slice):
            rv = []
            for i in self.__keys[item]:
                rv.append(self.__getattribute__(i))
        return rv

    def __setitem__(self, item, value):
        if isinstance(item, int):
            self.__setattr__(keys[item], value)
        elif isinstance(item, str):
            item = item.strip()
            keys = self.keys(item)
            if len(keys) == 0:
                is_valid_name = re.match('[a-zA-Z_]\w*$', item)
                if is_valid_name:
                    self.__setattr__(item, value)
                else:
                    raise ValueError, \
                          '"%s" is not a valid variable name' % item
            else:
                for k in keys:
                    self.__setattr__(k, value)
        elif isinstance(item, slice):
            stop = item.stop or len(self.__keys) 
            for i in range(*item.indices(stop)):
                self.__setattr__(self.__keys[i], value)

    def keys(self, filter=None, recursive=False):
        is_tree = lambda t: isinstance(t, Tree) and t.__keys <> []
        keys = self.__keys
        if filter:
            keys = filter_list(filter, keys)
        new_keys = []
        for k in keys:
            value = object.__getattribute__(self, k)
            new_keys.append(k)
            if is_tree(value) and recursive:
                new_keys += value.keys(filter, recursive)
        return new_keys
        
    def values(self, filter=None, recursive=False):
        is_tree = lambda t: isinstance(t, Tree) and t.__keys <> []
        keys = self.keys(filter)
        values = []
        for k in keys:
            value = object.__getattribute__(self, k)
            if is_tree(value):
                if recursive:
                    values += value.values(filter, recursive)
            else:
                values.append(value)
                
        return values
    
    def items(self, filter=None, recursive=False):
        keys = self.keys(filter)
        items = []
        for k in keys:
            value = object.__getattribute__(self, k)
            if isinstance(value, Tree):
                if recursive:
                    subs = value.items(filter, recursive)
                    if subs:
                        items.append((k, subs))
            else:
                items.append((k, value))
        return items

    def map(self, func, filter=None, recursive=False):
        # filter only applies to terminal node names
        keys = self.keys()
        for k in keys:
            value = object.__getattribute__(self, k)
            if isinstance(value, Tree):
                if recursive:
                    value.map(func, filter, recursive)
            else:
                if not filter or filter_list(filter, [k]):
                    self[k] = func(self[k])

    def nodecount(self, filter=None):
        c = 0
        keys = self.keys(filter)
        for k in keys:
            if isinstance(value, Tree):
                c += self[k].count(filter, recursive)
            else:
                c += 1 
        return c

    def sort(self, func=None):
        self.__keys.sort(func)





def test():
    a = Tree()
    a.b.c.d = 1
    print a.b.c.d == a.b['c']['d'] == a['b'][0][0] == a[0].c.d
    a.bb = 2
    print a['b+']
    #a[:].c.d = 2


        

if __name__ == '__main__':
    test()


