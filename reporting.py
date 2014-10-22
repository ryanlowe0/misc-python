# -*- coding: utf-8 -*-
import sys
import re

# shipping URLs
FEDEX = ('http://www.fedex.com/Tracking?ascend_header=1&clienttype=dotcom'
         '&cntry_code=us&language=english&tracknumbers=')
USPS = ('http://www.usps.com/shipping/trackandconfirm.htm?from=home'
        '&page=0035trackandconfirm')
ROYAL = 'http://www.royalmail.com/portal/rm'
UPS = 'http://www.ups.com/WebTracking/track?loc=en_US'

product_group_map = {"all": None,
                     "custom jacket": "bookjacket",
                     "card": "card",
                     "calendar": "calendar",
                     "gift certificate": "giftcert",
                     "book": "photobook"}

def formatDollars(num, curr_sym='$'):
    """Returns a dollar formatted string with the appropiate decimals, commas
    and dollar signs."""
    ipart, fpart = ('%0.2f' % num).split('.')
    comma = 0
    fmttd = ''
    for c in ipart[::-1]:
        fmttd = c + fmttd
        comma += 1
        if comma == 3:
            comma = 0
            fmttd = ',' + fmttd
    return '%s%s.%s' % (curr_sym, fmttd.lstrip(','), fpart)

def until(inStr, marker):
    if inStr is None: 
        return ''
    if marker in inStr:
        return inStr[:inStr.find(marker)]
    return inStr

def cover(color, material):
    if material and color:
        return '%s / %s' % (material, color)
    if color:
        return color
    if material:
        return material
    return 'N/A'

def flatten(inlist, ltype=(list,tuple), maxint=sys.maxint):
    if not isinstance(inlist, ltype):
        return inlist # just return the input unaltered if wrong type
    inlist = list(inlist)
    try:
        for i in xrange(maxint):
            while isinstance(inlist[i], ltype):
                # expand that list into the index (and subsequent indicies)
                inlist[i:i+1] = list(inlist[i])
    except IndexError:
        return inlist


def getLocation(activity_code, state, product, rework):
    jacketed = product in ('classic_bj', 'deluxe_bj')
    jacket_only = product in ('classic_cj', 'deluxe_cj')
    
    if state in ('CS-Hold', 'Error', 'Reject'):
        return state

    if rework and activity_code in ('imp', 'q-prt', 'rip', 'press', 'print',
                                    'rework', 'q-press', 'release',
                                    'batch-imp', 'q-prt-batch',
                                    'order-release', 'batch-add', 'mnfst',
                                    'batch-mnfst'):
        return 'Rework'
    
    if activity_code in ('imp', 'imp-j', 'q-prt', 'entry', 'rip', 'q-press',
                         'release', 'batch-imp', 'q-prt-batch',
                         'order-release', 'batch-add', 'jpeg', 'push-jpeg'):
        return 'Pre-Press'
    
    if activity_code == 'mnfst':
        if jacket_only:
            return 'Jacket Printer/QA-3'
        return 'Pressroom'
    
    if activity_code in ('resend', 'press', 'batch-mnfst'):
        return 'Pressroom'
    
    if activity_code == 'envl':
        return 'Card QA-2'

    if activity_code == 'print':
        return 'Drying Rack'
    
    if activity_code == 'cut':
        if product in ('card', 'postcard'):
            return 'Envelope Select/Print'
        if product == 'pocket':
            return 'Softcover Bind/QA-2'
        if product == 'calendar':            
            return 'Calendar Assembly'        
        return 'Hardcover Collating'
    
    if activity_code == 'collate':
        return 'Staple/QA-1'
    
    if activity_code == 'qa-1':
        return 'Hardcover Bind/QA-2'
    
    if jacketed and activity_code in ('qa-2', 'jckt'):
        return 'Jacket Printer/QA-3'
    
    if activity_code in ('qa-2', 'qa-3'):
        return 'Packing'
    
    if activity_code == 'pack':
        return 'Shipping'

    return activity_code
