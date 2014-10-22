

class odict(dict):
    '''odict is an Object Dictionary.  It subclasses builtin dict object.
    It allows dot (.) syntax.
    
    The the following become equivalent:

        order.book.product_id    same as    order['book']['product_id']
    '''    

    def __init__(self, indict={}):
        dict.__init__(self)
        self.update(indict)
        self.__dict__.update(indict)

    def __setitem__(self, item, value):
        self.__dict__[item] = value
        dict.__setitem__(self, item, value)

    def __setattr__(self, item, value):
        self.__setitem__(item, value)
        
    def __getitem__(self, item):
        try:                # attempt to retrieve normally
            return dict.__getitem__(self, item)
        except KeyError:    # otherwise try attribute
            try:
                return self.__getattribute__(item)
            except AttributeError, e:
                raise KeyError(str(e))


