
from sqlalchemy import func, Column
from sqlalchemy.sql import and_, select
from plant.utils import all_in
from plant.odict import odict
from plant.dbengine import transactional
from plant.modelaliases import *

FACTS = {'gross': func.sum(oi.gross / er.rate), 
         'orders': func.count(oi.order_item_id),
         'active_orders': func.count(wi.order_item_id),
         'net': func.sum(oi.net / er.rate), 
         'pages': func.sum(pi.num_pages),
         'revenue': func.sum((oi.net + oi.shipping) / er.rate),
         'shipping_cost': func.sum(i.shipping_cost), 
         'shipping': func.sum(oi.shipping / er.rate), 
         'tax': func.sum(oi.tax / er.rate), 
         'units': func.sum(oi.qty)}
for f in FACTS: FACTS[f] = FACTS[f].label(f)

DIMENSIONS = {'activity': act.name,
              'activity_code': act.code,
              'activity_date': wi.last_updated,
              'canceller': cu.username,
              'cancel_date': o.cancel_date,
              'cancel_reason': can.comments,
              'charge_date': pay.payment_date,
              'client': sc.name,
              'comments': 
                select([func.group_concat(oc.txt)])
                .where(o.order_id == oc.order_id)
                .correlate(o.__table__),
              'cover_color': cc.name,
              'cover_material': cm.name,
              'currency': cur.code,
              'customer_name': 
                func.concat_ws(' ', cus.first_name, cus.last_name),
              'destination': func.concat_ws(', ', a.city, a.state, a.country),
              'email': e.email,
              'error_date': err.error_date,
              'error_reason': err.error_reason,
              'foid': oi.order_item_id,
              'gross': oi.gross,
              'last_update': func.date(wi.last_updated),
              'location': lv.location,
              'net': oi.net,
              'order_date': func.date(o.order_date),
              'order_datetime': o.order_date,
              'pages': pi.num_pages,
              'total_pages': oi.qty * pi.num_pages,
              'partner': par.name,
              'pdf': func.concat_ws('/', dwn.uri, pi.product_file),
              'press_routing': 
                select([pr.code])
                .where((pr.product_id == oi.product_id) &
                       (pr.cover_type_id == oif.cover_type_id) &
                       (pr.active == 1)),
              'product': p.name,
              'product_code': pct.code,
              'product_name': pct.name,
              'product_type': pt.name,
              'promo': pro.code,
              'qty': oi.qty,
              'reference': o.reference_number,
              'rework_date': r.rework_date,
              'rework_qty': r.qty,
              'rework_reason': rr.name,
              'ship_country': c.name,
              'ship_date': i.ship_date,
              'ship_method': sm.name,
              'state': s.name,
              'theme': t.name,
              'turnaround':
                select([func.least(func.sum(cal.is_business_day), 7)])
                .where((cal.calendar_date >= func.date(o.order_date)) &
                       (cal.calendar_date <= i.ship_date))}
for d in DIMENSIONS: DIMENSIONS[d] = DIMENSIONS[d].label(d)

JOINS = {a:   a.address_id == o.shipping_address_id,
         act: wi.activity_id == act.activity_id,
         c:   a.country == c.country_code,
         can: (can.order_item_id == oi.order_item_id) &
              can.activity_id.in_([42, 43]),
         cu:  cu.user_id == can.user_id,
         cur: cur.currency_id == o.currency_id,
         cus: cus.customer_id == o.customer_id,
         cc:  oif.cover_color_id == cc.cover_color_id,
         cm:  oif.cover_material_id == cm.cover_material_id,
         dwn: pi.download_path_id == dwn.uri_resource_id,
         e:   e.email_id == o.email_id,
         er:  (er.rate_date == func.date(o.order_date)) &
              (er.currency_id == o.currency_id),
         err: err.order_item_id == wi.order_item_id,
         i:   oi.order_item_id == i.order_item_id,
         lv:  lv.order_item_id == oi.order_item_id,
         o:   o.order_id == oi.order_id,
         od:  od.order_id == o.order_id,
         oif: oif.order_item_id == oi.order_item_id,
         pct: (pct.product_id == oi.product_id) &
              (pct.cover_type_id == oif.cover_type_id),
         p:   oi.product_id == p.product_id,
         par: par.partner_id == o.partner_id,
         pay: i.invoice_id == pay.invoice_id,
         pi:  pi.product_item_id == oi.product_item_id,
         pro: pro.promotion_id == od.promotion_id,
         pt:  pt.product_type_id == p.product_type_id,
         r:   r.order_item_id == oi.order_item_id,
         rr:  rr.rework_reason_id == r.rework_reason_id,
         s:   s.state_id == wi.state_id,
         sc:  sc.software_client_id == sv.software_client_id,
         sm:  sm.shipping_method_id == o.shipping_method_id,
         sv:  sv.software_version_id == o.software_version_id,
         t:   t.theme_id == pi.theme_id,
         wi:  wi.order_item_id == oi.order_item_id}

class DataCube(object):
        
    @transactional
    def getData(self, session, facts, dimensions, filters=[]):
        """General purpose summary data generator.
        """

        for n, f in enumerate(filters):
            dc = odict(DIMENSIONS)
            if isinstance(f, (str, unicode)):
                filters[n] = eval(f)

        fact_aliases = facts[:]
        facts = []
        for f in fact_aliases:
            if f not in FACTS:
                raise ValueError('Unknown fact: %s' % f)
            facts.append(FACTS[f])
            
        dim_aliases = dimensions[:]
        dimensions = []
        for d in dim_aliases:
            if d not in DIMENSIONS:
                raise ValueError('Unknown dimension: %s' % d)
            dimensions.append(DIMENSIONS[d])

        cols = dimensions + facts
        conds = []
        self._gatherConds(cols + filters, conds)
        q = session.query(*cols).filter(and_(*(conds + filters)))
        if facts:
            q = q.group_by(dimensions)
        #print q#;return []
        return q.all()


    def _gatherConds(self, attrs, conds):
        """Gather the conditions required to do the appropriate joins for the
        selected columns filters requested if any."""
        # Go through the expression recursively, examining the columns
        # associated with the given attributes as they are encountered,
        # checking the conds list as it's being built for the existence of a
        # model class with the matching table to see whether that associated
        # join condition is defined, adding it when not.
        if isinstance(attrs, list):
            for a in attrs:
                self._gatherConds(a, conds)
        elif hasattr(attrs, "get_children"):
            children = attrs.get_children()
            for child in children:
                if isinstance(child, Column):
                    for cls, clause in JOINS.items():
                        if cls.__table__ == child.table:
                            if str(clause) not in map(str, conds):
                                conds.append(clause)
                                self._gatherConds(clause, conds)
                else:                    
                    self._gatherConds(child, conds)
        

