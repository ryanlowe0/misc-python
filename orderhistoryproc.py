# -*- coding: utf-8 -*-

from datetime import datetime
from plant.odict import odict
from plant.sautils import todict
from plant.dbengine import transactional
from plant.controllers.histories import Histories
from plant.controllers.attributes import Attributes


class OrderHistoryError(Exception): pass

class OrderHistoryProc(object):

    def __init__(self):
        self.histories = Histories()
        self.activities = Attributes('Activity')
    
    @transactional
    def getData(self, session, order_item_id=None, batch_id=None,
                product_item_id=None):

        entity_name, entity_id = self._getEntityId(order_item_id, 
                                                   batch_id, 
                                                   product_item_id)
        
        if entity_name == 'order_item_id':
            history = self.histories.getHistory(order_item_id)
            #from reworks import Reworks
            #rework_data = Reworks().getReworks(order_item_id)
        elif entity_name == 'batch_id':
            history = self.histories.getBatchHistory(batch_id)
        else:   # product_item
            history = self.histories.getProductHistory(product_item_id)

        history = [odict(todict(h)) for h in history]
        for s in history:
            if not isinstance(s.history_date, datetime):
                s.history_date = datetime(*s.history_date.tuple()[:6])
            
            for attr in ('code', 'name', 'description'):
                func = getattr(self.activities, 'get%s' % attr.title())
                try:
                    setattr(s, 'activity_' + attr, func(s.activity_id))
                except: 
                    setattr(s, 'activity_' + attr, '')

            if s.entity_type == 'order_item':
                s.entity_name = 'Order'
            elif s.entity_type == 'batch':
                s.entity_name = 'Batch'
            else:
                s.entity_name = 'Product'
            s.entity_type += '_id'

            """
            # show rework reason in comment
            if s.activity_id == 'REWORK':
                for r in rework_data:
                    if not isinstance(r['date'], datetime):
                        r['date'] = datetime(*r['date'].tuple()[:6])
                    if s.history_date == r['date']:
                        if r['rework_reason']:
                            s.comments += ' %s' % r['rework_reason']
            """

            s.comments = (s.comments or '').replace('*', '').strip()
            if s.entity_type == 'batch_id' and s.activity_code == 'entry':
                s.comments += '''
                <a href="batchdetails.py?batch_id=%s">Batch %s Details</a>
                ''' % (s.batch_id, s.batch_id)

            s.username = s.user.username or ''

            # change to string, add bolding
            s.history_date = '<strong>%s</strong> %s' % (s.history_date.date(),
                                                         s.history_date.time())
            # make 'order entry' and 'start over' activities in bold:
            s.bold = (s.activity_code == 'entry' and 
                      s.entity_type   == 'order_item_id' or 
                      s.activity_code in ('resend', 'rework', 'aging'))

        return history
        

    def _getEntityId(self, order_item_id, batch_id, product_item_id):
        """Parse args to determine which entity_id is not None,
           ensuring that there is only one.

           Return entity name and value.
        """
        entity_name = ''
        for name in 'batch_id', 'order_item_id', 'product_item_id':
            id = eval(name)
            if id is not None:
                if entity_name:
                    raise OrderHistoryError('Only one id may be provided')
                entity_id = id
                entity_name = name
        if not entity_name:
            raise OrderHistoryError('No valid ids were provided')
        return entity_name, entity_id

