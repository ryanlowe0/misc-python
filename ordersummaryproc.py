
from decimal import Decimal
from sqlalchemy import func, desc
from plant.dbengine import transactional
from plant.smartdate import Date
from plant.odict import odict
from datacube import DataCube
from reporting import formatDollars, until


MONEY_FIELDS = ('gross', 'net', 'revenue', 'shipping', 'shipping_cost', 'tax')

class OrderSummaryProc(object):
    '''Provides data for use by order summary reports.'''
    
    def label(self, data, attr):
        '''Map attributes to display names.'''
        if attr.endswith('date'):
            return str(Date(data))
        if attr == 'last_update':
            age = Date() - Date(data)
            if age < 0:  return 'Unknown'
            if age == 0: return 'Today'
            if age == 1: return 'Yesterday'
            return '%s Days Ago' % age
        if attr == 'turnaround':
            if data is None: return ''
            data -= 1
            if data == 0: return 'Same Day'
            if data == 1: return 'Next Day'
            if data < 6:  return 'Within %s Days' % data
            return '6 or More Days'
        return data

    @transactional
    def getData(self, session, params):
        '''Get the order summary data based on the given parameters.'''

        from web.htmlutil import Encryption
        encrypt = Encryption().simple_encrypt
        cube = DataCube()
        data_tables = []
        filters = params.filters
        facts = params.get('facts', ['orders'] * len(params.dims))
        # extras are additional facts that will display in columns to
        # the right of the group by columns
        extra = params.get('extra_cols', [])
        # ratio data <A>_per_<B> computed from A and B, such that
        # division of B occurs only after all A's are summed up
        extra_facts = [e for e in extra if '_per_' not in e]
        for i, dims in enumerate(params.dims):
            fact = facts[i]
            percent_dims = [d.endswith('_percent') for d in dims[1:]]
            percent_cols = []
            dims = [d.replace('_percent', '') for d in dims]
            # main dimension used to title the table
            row_dim = dims[0]
            dim_name = ' '.join(s.title() for s in row_dim.split('_'))
            data = odict({'title': fact.title(), 'row_name': dim_name,
                          'cols': [], 'rows': [], 'body': [], 'dims': dims})
            if any(percent_dims):
                data.title = '%s Percentages' % data.title.rstrip('s')
            filter_str = ''
            if filters:
                filter_str = ';'.join(filters) + ';'
            for d in sorted(cube.getData(session, [fact] + extra_facts, 
                                         dims, filters[:])):
                #print d, '<br/>'
                row_val = getattr(d, row_dim)
                if row_val not in data.rows:
                    if not row_val: continue
                    data.rows.append(row_val)
                    data.body.append({row_dim: row_val, 'Total': 0, 
                                      'detail_params': {}})
                row_filter_str = filter_str + "dc.%s == '%s'" % \
                                 (dims[0], row_val)
                for g, col_dim in enumerate(dims[1:]):
                    key = getattr(d, col_dim)
                    # grouping is to ensure proper column ordering
                    if len(data.cols) < g + 1:
                        data.cols.append([])
                        percent_cols.append([])
                    if key not in data.cols[g]:
                        data.cols[g].append(key)
                        percent_cols[g].append(percent_dims[g])
                    if key not in data.body[-1]:
                        data.body[-1][key] = 0
                    val = getattr(d, fact)
                    data.body[-1][key] += val
                    data.body[-1]['Total'] += val
                    p = row_filter_str + ";dc.%s == '%s'" % (dims[1], key)
                    data.body[-1]['detail_params'][key] = encrypt(p)
                for e in extra:
                    if e not in data.body[-1]:
                        data.body[-1][e] = 0
                    if '_per_' in e:
                        # just numerator part of ratio data
                        num = e.split('_per_')[0]
                        data.body[-1][e] += getattr(d, num)
                    else:
                        data.body[-1][e] += getattr(d, e)
                data.body[-1]['detail_params']['Total'] = \
                    encrypt(row_filter_str)
            data.cols = [c for g in data.cols for c in g]       # flatten cols
            percent_cols = [c for g in percent_cols for c in g] # flatten cols
            # only show total column if there are more than 1 col to sum
            if len(data.cols) > 1:
                data.cols.append('Total')
                percent_cols.append(percent_cols[-1])
            data.cols += extra
            percent_cols += [False] * len(extra)
            data.total_row = {'detail_params': {}}
            # add 0 for missing values, populate total row and detail filters
            for col in data.cols:
                for row in data.body:
                    if col not in row:
                        row[col] = 0
                data.total_row[col] = sum(row[col] for row in data.body)
                if col not in extra:
                    p = filter_str + "dc.%s == '%s'" % (dims[1], col)
                    data.total_row['detail_params'][col] = encrypt(p)
            # apply special formatting, 
            # divide denominator part of ratio data and percents
            data.col_names = []
            for i, col in enumerate(data.cols):
                for row in data.body + [data.total_row]:
                    if '_per_' in col:
                        div = col.split('_per_')[1] + 's'
                        if div == fact:
                            row[col] /= Decimal(row.get('Total', 1) or 1)
                        else:
                            row[col] /= Decimal(row[div] or 1)
                    elif percent_cols[i]:
                        if col == 'Total':
                            div = Decimal(data.total_row['Total'])
                        else:
                            div = Decimal(row['Total'])
                        row[col] *= 100 / (div or 1)
                    if col.split('_per_')[0] in MONEY_FIELDS:
                        row[col] = formatDollars(row[col])
                    elif percent_cols[i] and row[col]:
                        row[col] = '%0.1f%%' % row[col]
                    elif isinstance(row[col], (float, Decimal)) and \
                         row[col] <> int(row[col]):
                        row[col] = '%0.4f' % row[col]
                data.col_names.append(' '.join(s.replace('usd', '$').title() 
                                               for s in col.split('_')))
            data_tables.append(data)
        #for b in data_tables[0].body:
        #    print [(k, v) for k,v in b.items() if k <> 'detail_params'], '<br/>'
        return data_tables
        
        
    def getFilters(self, params):
        '''Translate parameters into sqlalchemy filter conditions'''

        filters = params.get('filters', [])
        if isinstance(filters, str):
            filters = filters.split(';')
        try:
            start_date = Date([params.startYear, params.startMon, 
                               params.startDay])
        except:
            start_date = None
        try:
            end_date = Date([params.endYear, params.endMon, params.endDay])
        except:
            end_date = Date()
        if 'start_date' in params:
            start_date = Date(params.start_date)
        if 'end_date' in params:
            end_date = Date(params.end_date)
        #start_date = Date('2009-11-11')
        #end_date = Date('2009-11-20')
        if start_date:
            params.drange = '%s - %s' % (start_date.format('%B %d, %Y'),
                                         end_date.format('%B %d, %Y'))
            end_date += 1   # to account for hours/min/sec 
            params.date_span = end_date - start_date
            if 'dtype' not in params or params.dtype == 'order_date':
                dtype = 'o.order_date'
            elif params.dtype == 'charge_date':
                dtype = 'pay.payment_date'
            elif params.dtype == 'ship_date':
                dtype = 'i.ship_date'
            elif params.dtype == 'cancel_date':
                dtype = 'can.history_date'
            # if row dim is order_date, use dtype instead
            for i, d in enumerate(params.dims):
                params.dims[i][0] = d[0].replace('order_date',
                                                 params.dtype)
            filters += ["%s >= '%s'" % (dtype, start_date.to_dt()),
                        "%s < '%s'"  % (dtype, end_date.to_dt())]
        else:
            filters += ['wi.state_id < 500']
        if 'cover_material' in params:
            filters += ["cm.code == '%s'" % params.cover_material]
        if 'product' in params:
            filters += ["p.code == '%s'" % params.product]
        if 'client' in params:
            filters += ["sc.code == '%s'" % params.client]
        if 'product_type' in params:
            filters += ["pt.code == '%s'" % params.product_type]
        if 'country' in params:
            if params.country == 'US':
                filters += ["a.country == 'US'"]
            elif params.country == 'UK/EU':
                filters += ["a.country <> 'US'"]
        if params.get('partner') not in ('All', None):
            filters += ["par.name == '%s'" % params.partner]
        # <A>_per_order -> <A>_per_<unit|page>
        if 'avetype' in params and params.avetype <> 'per_order':   
            extra = []
            for e in params.extra_cols:
                if '_per_' not in e or e.endswith(params.avetype) or \
                   e.startswith(params.avetype[4:] + 's'):
                    extra.append(e)
                else:
                    new = until(e, 'per_') +  params.avetype
                    if new <> 'units_per_page': # remove this silly fact
                        extra.append(until(e, 'per_') +  params.avetype)
            params.extra_cols = extra
        return filters


       
