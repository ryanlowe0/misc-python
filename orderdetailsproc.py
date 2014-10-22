
from sqlalchemy import func, desc
from sqlalchemy.sql import and_
from plant.dbengine import transactional
from plant.smartdate import Date
from plant.odict import odict
from plant.utils import in_any
from plant.model import BatchHistory, BatchItem, OrderItemHistory
from plant.resources import res
from web.htmlutil import Encryption
from datacube import DataCube


DEFAULT_FIELDS = ['foid', 'reference', 'order_datetime', 'product_name', 
                  'destination', 'qty', 'pages', 'comments']

SPECIAL_FIELDS = ['print_date', 'press', 'operator', 'batch_id', 
                  'unerror_button']


class OrderDetailsProc(object):
    '''Provides data for use by the order details report.'''

    def __init__(self):
        self.predefined = res.conf.reports.predefined
    
    def label(self, field):
        return ' '.join(w.title() for w in field.split('_'))\
                  .replace('Order Datetime', 'Order Date')\
                  .replace('Press Routing', '')\
                  .replace('Pdf', 'Files')\
                  .replace('Unerror Button', '')

    def getFields(self, rpt):
        return self.predefined.get(rpt, {}).get('fields', DEFAULT_FIELDS)
    
    @transactional
    def getData(self, session, rpt, filters):
        '''Get the order details data based on the given parameters.'''


        e = Encryption()
        filters = e.simple_decrypt(filters).split(';')
        fields = self.getFields(rpt)
        cube_fields = [c for c in fields if c not in SPECIAL_FIELDS]
        data = []

        for dc in DataCube().getData(session, [], cube_fields, filters):
            d = odict(zip(cube_fields, dc))
            if self.predefined[rpt].get('barcoded'):
                d.barcoded = True
            rework = 'rework_date' in fields
            if 'print_date' in fields or 'batch_id' in fields:
                hist_batch_id = session.query(BatchItem.batch_id)\
                                .filter((BatchItem.order_item_id == d.foid) &
                                        (BatchItem.active == 1))\
                                .order_by(desc(BatchItem.created))\
                                .scalar()

            if 'print_date' in fields:
                if hist_batch_id:                    
                    dt = session.query(BatchHistory.history_date)\
                         .filter(BatchHistory.batch_id == hist_batch_id)\
                         .order_by(BatchHistory.history_date)\
                         .scalar()
                else:
                    dt = session.query(OrderItemHistory.history_date)\
                         .filter(OrderItemHistory.order_item_id == d.foid)\
                         .order_by(OrderItemHistory.history_date)\
                         .scalar()
                d.print_date = dt

            if 'batch_id' in fields:
                d.batch_id = hist_batch_id

            if ('press' in fields or 'operator' in fields) and rework:
                d.press = ''
                d.operator = 'Unknown'
                bh = session.query(BatchHistory)\
                     .join((BatchItem, (BatchItem.batch_id ==
                                        BatchHistory.batch_id)))\
                     .filter((BatchItem.order_item_id == d.foid) &
                             ((BatchItem.removed_date == None) |
                              (BatchItem.removed_date > d.rework_date)) &
                             (BatchHistory.history_date < d.rework_date) &
                             (BatchHistory.activity_id.in_([16, 17, 20, 24])))\
                      .order_by(desc(BatchHistory.history_date))\
                      .first()
                if bh:
                    d.press = bh.comments.split(' ')[-1]
                    d.operator = bh.user.username
                else:
                    oh = session.query(OrderItemHistory)\
                         .filter((OrderItemHistory.order_item_id == d.foid) &
                                 (OrderItemHistory.history_date < 
                                  d.rework_date) &
                                 (OrderItemHistory.activity_id.in_(
                                    [16, 17, 20, 24])))\
                         .order_by(desc(OrderItemHistory.history_date))\
                         .first()
                    if oh:
                        d.press = oh.comments.split(' ')[-1]
                        d.operator = oh.user.username
                    
            if 'pdf' in fields:
                import os.path
                d.pdfname = os.path.basename(d.pdf)
                d.dime = d.pdf.replace('hires/', 'share/dime_backup/').replace('.pdf', '.dime')
                d.log = "http://wcom.mypublisher.com/merc/cutomertransform" \
                        "details.asp?filename=%s" % os.path.basename(d.dime)

            data.append(d)
            
        return data
