#!/usr/local/bin/python

import re, cgi
from kid import Template
from plant.dbengine import transactional
from plant.odict import odict
from plant.smartdate import Date
from plant.model import GCReport, GiftCertificate, OrderItem
from web.reportutils import HTML


class GiftCertProc(object):
    '''Provides data for use by the gift certificate report.'''

    @transactional
    def getData(self, session, params):
        q = session.query(GCReport)
        q = q.filter(GCReport.activity_date < params.end_date)
        if params.start_date:
            q = q.filter(GCReport.activity_date >= params.start_date)
        else:   # open GCs
            q = q.join((GiftCertificate, GiftCertificate.gc_code == 
                                         GCReport.gc_code),
                        (OrderItem, OrderItem.order_item_id == 
                                    GCReport.order_item_id))\
                 .filter((GiftCertificate.amount > GiftCertificate.redeemed) &
                         (OrderItem.state_id <= 500))    # not cancelled

        if params.activity <> 'All':
            q = q.filter(GCReport.activity_type == params.activity)
        q = q.order_by('activity_date')
        return q.all()
