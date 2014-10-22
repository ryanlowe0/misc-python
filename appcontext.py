#!/usr/bin/python

# $Id: appcontext.py 2105 2008-12-15 21:56:36Z dlink $

'''
Plant Application Context

APPS stores a list of the most common modules and classes for Plant
code. APP_MAP maps each with the code needed to import and instantiate
the apps. The map is meant to be added to the props dict of a LazyAttr 
derived class, making the apps available as member attributes when
needed, but requiring little overhead when not used.


Example usage:

class A(AppContext): pass
a = A()
print a.logger.name

class B(LazyDictAttr):
    def __init__(self, props={}):
        props = {'extra1': 'initCode1()',
                 'extra2': 'initCode2()'}
        import appcontext
        props.update(APP_MAP)
        LazyDictAttr.__init__(self, props)
'''


APP_MAP = {
    'activities':     "__import__('activities').Activities()",
    'bookattributes': "__import__('bookattributes')",
    'cards':          "__import__('cards').Cards()",
    'calendars':      "__import__('calendars').Calendars()",
    'config':         "__import__('config').factory.create()",
    'db':             "__import__('db').factory.create()",
    'logger':         "__import__('logit').getLogger(self.__class__.__name__)",
    'batches':        "__import__('batches').Batches()",
    'books':          "__import__('books').Books()",
    'orders':         "__import__('orders').Orders()",
    'presses':        "__import__('presses').Presses()",
    'pressRouting':   "__import__('pressrouting').PressRouting()",
    'printReasons':   "__import__('printreasons').PrintReasons()",
    'products':       "__import__('products').Products()",
    'shares':         "__import__('shares').Shares()",
    'workflow':       "__import__('workflow').Workflow()"
    }
APPS = APP_MAP.keys()

from lazyattr import LazyAttr
class AppContext(LazyAttr):
    def __init__(self, props={}):
        props.update(APP_MAP)
        LazyAttr.__init__(self, props)



print APPS
