# $Id: $

# Ryan Lowe 2006

import os, sys
import yaml
import genpdf
from resources import res
from odict import odict

DEBUG = 0

conf = res.conf.imposition

ENVELOPE_WIDTH = 522
ENVELOPE_HEIGHT = 378

DEBUG_PAGE_NAMES = 0


class ImposeError(Exception): pass

class OrderData:
    def __init__(self, order_item_id):
        from controllers import orders, histories
        from sautils import todict
        order_ctrl = orders.Orders()
        i = order_ctrl.getOrderItem(order_item_id)
        o = order_ctrl.getOrder(i.order_id)
        f = i.feature
        pi = i.product_item
        flags = o.flags or ''
        try: 
            self.orientation = pi.orientation
        except: 
            self.orientation = ''
        try:
            self.print_return_address = 'return_address' in flags
            self.return_address = '\n'.join(o.return_address).strip()
        except:
            self.print_return_address = 0
            self.return_address = ''
        sa = todict(o.shipping_address)
        self.address = ('%(address1)s %(address2)s %(address3)s'
                        ' %(city)s, %(state)s %(zip_code)s %(country)s') % sa
        self.archive_dir = pi.product_path
        self.pdfname = pi.product_file
        self.comments = []
        no_20_20 = False
        self.code = f.press_routing.code or ''
        self.page_siding = f.page_siding_id
        p, c, s = i.product.name, '', f.page_siding.name
        if f.cover_type_id:
            c = f.cover_type.name
        self.product = '%s %s %s' % (p, c, s)
        self.qty = self.order_qty = i.qty
        # workorder comments
        hist_ctrl = histories.Histories()
        if hist_ctrl.activityInHistory(order_item_id, 'rework'):
            self.comments.append('REWORK')
        if o.partner_id > 0:
            no_20_20 = True
            self.comments.append('%s Order' % o.partner.name)
        if sa['country'] != 'US':
            no_20_20 = True
            self.comments.append('International Order')
        if no_20_20:
            self.comments.append('No 20/20')
        if order_ctrl.isLargeDollarOrder(order_item_id):
            self.comments.append('Special QA Handling')
        if 'vip_order' in flags:
            self.comments.append('VIP Order')
        self.comments = ' '.join(self.comments)
        self.cover = '%s %s' % (f.cover_color.name, f.cover_material.name)
        if self.cover.startswith('N/A'):
            self.cover = ''
        self.cover_swatch_file = f.cover_color.code + '.jpg'
        self.date = str(o.order_date)[:10]
        self.flag = sa['country']
        if self.flag not in ('US', 'CA'): 
            self.flag = 'EU'
        self.order_item_id = int(order_item_id)
        self.method = o.shipping_method.name
        self.order_number = o.reference_number
        self.pages = pi.num_pages
        self.show_cover = f.cover_type_id not in (1, 2) # not pic-win/jacket
        self.staple = order_ctrl.getStapleWeight(order_item_id)
        # jacket only orders use same imp codes as jacketed books
        if f.cover_type_id == 2:        # jacket
            if not self.code:
                self.barcode_suffix = 'JO'
                if i.product_id == 8:   # classic jacket
                    self.code = 'H'
                else:
                    self.code = 'J'
            else:
                self.barcode_suffix = 'J'
        elif f.cover_type_id == 5:      # photo finish
            self.barcode_suffix = 'P'
        else:
            self.barcode_suffix = ''
                
    def __str__(self): return str(self.__dict__)
    

class ImpData(odict):
    'Imposition data object'
    def __init__(self, data={}):
        defaults = conf.defaults
        if data.get('order_item_id'):    # use order data 
            defaults.update(OrderData(data['order_item_id']).__dict__)    
        defaults.update(data)
        odict.__init__(self, defaults)
        if not self.order_item_id: 
            self.order_item_id = 0
        self.print_reason = str(self.print_reason).replace('new', '')
        if self.code in 'KL':
            if self.print_reason:
                self.cover = ''
            else:
                from controllers import products
                self.cover = products.getEnvBundleMsg(self.qty)
                self.envelope_qty = products.getEnvQty(self.qty)
        # make sure cover pages are in the front of the page list
        if 'page_list' in self:
            new = []
            for p in self.page_list or []:
                if str(p).lower() in ('cover', 'jacket'):
                    new = [p] + new
                else:
                    new.append(p)
            self.page_list = new
        # auto-detect page count
        if self.pages is None:
            pdf = os.path.join(self.archive_dir, self.pdfname)
            self.pages = genpdf.countPages(pdf)
        self.pages = int(self.pages or 0)
        if 'mail_merge' in self:
            self.batched = True

    
def imposeCovers(order_item_ids, quantity=None, suffix='', filename='', 
                 type='cover', output_dir=None):
    suffix = suffix.strip('-') + '-'
    pr = suffix[:suffix.find('-')]
    data = []
    if not order_item_ids:
        return ''
    hi = lo = int(order_item_ids[0])
    for order_item_id in map(int, order_item_ids):
        if order_item_id < lo: lo = order_item_id
        if order_item_id > hi: hi = order_item_id
        d = {'order_item_id': order_item_id, 'print_reason': pr, 
             'page_list': [type], 'batched': True}
        if quantity:
            d['qty'] = quantity
        code = ImpData(d).code
        imp_type = conf.metadata[code].cover
        data.append(d)
    lohi = '-%s-%s-' % (lo, hi)
    fn = '%(code)s' + lohi + type + 's-%(print_reason)s-%(sheets)s-1.pdf'
    if filename:
        fn = filename
    imp = Imposition()
    return imp.impose(data, fn, imp_type, output_dir)
    

def imposeBatch(batch_id, components=[], print_run=0):
    from controllers.batches import Batches
    from ibatches import BatchesInterface
    ibatch = BatchesInterface()
    batch = Batches().getBatch(batch_id)
    fns = []
    data = [{'order_item_id': i.order_item_id, 'qty': i.qty, 'batched': True,
             'print_reason': batch.print_reason.code,
             #'page_list': [p.page for p in i.pages for n in range(p.qty)],
             'manifest_title': 'BATCH %s' % batch_id}
            for i in batch.items if i.active]
    if not data:
        return []
    imp = Imposition()
    batch_components = [c for c in batch.components 
                        if c.print_run == print_run]
    for batch_component in batch_components:
        if components and batch_component.component.name.lower() \
           not in components:
            continue
        product_component = [c for c in batch.product.product_components
                             if c.component_id == 
                             batch_component.component_id][0]
        if not product_component.needs_queueing:
            continue
        type = None
        data2 = [d.copy() for d in data]
        print_qty = ibatch.getPrintQty(batch, batch_component)
        # large batch - impose only pages-per-side copies
        if print_qty > 1:
            if len(data2) <> 1:
                msg = 'Only single item batches may have print-qty > 1'
                imp.logger.error(msg)
                raise ImposeError(msg)
            data2[0]['qty'] = batch.product.pages_per_side
            data2[0]['print_qty'] = print_qty
            del data2[0]['manifest_title']
            data2[0]['no_manifest'] = True
        if batch_component.component.code.endswith('covers'):
            for d in data2:
                code = ImpData(d).code
                d['page_list'] = ['cover']
                type = conf.metadata[code].cover
        fn = batch_component.press_filename
        if product_component.single_pdf:
            fn = imp.impose(data2, fn, type)
            fns.append(fn)
        else:
            for d in data2:
                if batch_component.component.code.endswith('env') and \
                   not ImpData(d).print_return_address:
                    continue
                fn = imp.impose([d], fn, type)
                fns.append(fn)
    return fns


def imposeContent(order_item_id, suffix=''):
    suffix = suffix.strip('-').split('-')
    pr = ''
    if suffix:
        pr = suffix[0]
    fn = '%(code)s%(staple)s-%(order_item_id)s-content-' \
         '%(print_reason)s-%(sheets)s-%(qty)s.pdf'
    d = {'order_item_id': order_item_id, 'print_reason': pr}
    if len(suffix) > 1:
        d['qty'] = suffix[1]
    o = ImpData(d)
    imp = Imposition()
    if o.pages < 2:
        msg = 'PDF has no content pages: %s' % order_item_id
    elif o.pages > 101:
        msg = 'PDF has too many pages (101 limit): %s' % order_item_id
    else:
        return imp.impose([d], fn)
    raise ImposeError(msg)


def imposeJackets(order_item_ids, quantity=None, suffix='', 
                  output_dir=conf.printer_dir):
    return imposeCovers(order_item_ids, quantity, suffix, 
                        type='jacket', output_dir=output_dir)


def imposeEnvelope(order_item_id):
    fn = '%(code)s-%(order_item_id)s-envelopes-%(sheets)s-1.pdf'
    d = {'order_item_id': order_item_id}
    imp = Imposition()
    return imp.impose([d], fn)


def imposeMailMerge(data, num=1):
    'Create numbered files until merge data is exhausted.'
    import csv
    if 'code' not in data:
        data['code'] = 'small K'
    d = ImpData(data)
    mm = [x for x in csv.reader(file(d['mail_merge']))]
    mm.pop(0)
    fns = []
    name = d['mail_merge'].rstrip('.csv')
    # qty per file
    qty = int(d['qty'] or 0)
    d['no_manifest'] = True
    imp = Imposition()
    while True:
        d['mail_merge'] = mm[:qty]
        d['qty'] = len(d['mail_merge'])
        fn = imp.impose([d], '%s-%s' % (name, num) + '-%(qty)s.pdf')
        fns.append(fn)
        mm = mm[qty:]
        num += 1
        if not mm:
            return fns
    


def imposePages(order_item_id, pages):
    d = {'order_item_id': order_item_id, 'page_list': pages, 'batched': True, 'qty': 1}
    imp = Imposition()
    return imp.impose([d], '%(code)s-%(order_item_id)s-pages-rework-%(sheets)s-1.pdf')



def hasBarcodePage(order_item_id):
    'Is barcode on a separate page?'
    imp = Imposition()
    data = ImpData({'order_item_id': order_item_id})
    meta_data = conf.metadata[data.code]
    psuedo_simplex = data.page_siding == 1 and 'cover' in meta_data
    return len(imp.addBarcode(data, psuedo_simplex)) == 2


class Imposition(object):
    def __init__(self):
        self.logger = res.getLogger(self)

    def addBarcode(self, data, psuedo_simplex):
        ' Add appropriate barcode/logo combination for a given job type '
        o = data
        barcode = ['barcode', (), o]
        logo = ['logo', (), o]
        logobarcode = ['logo/barcode', (), o]
        blank = ['blank', (), o]
        if o.code in 'CDKLSU':  # printed covers
            # blank back of last page
            if psuedo_simplex or not o.pages & 1:
                return [blank]
            return []
        # add to back of new page if duplex and even page count
        # (actually check for odd because cover is included)
        if not psuedo_simplex and o.pages & 1 and o.code <> 'M':
            if o.code in 'FJ': 
                return [blank, barcode]
            return [blank, logobarcode]
        # no logo on deluxe books
        if o.code in 'EFIJ':
            return [barcode] 
        return [logobarcode]


    def createSheetMap(self, page_list, rows, cols, duplex, front_sheet=None):
        ' Create 2d sheet map from 1d page list '
        sheet_map = []
        for i in range(rows):
            sheet_map.append([])
            for j in range(cols):
                sheet_map[i].append([])
        pages = len(page_list)
        pages_per_sheet = rows * cols
        sheets = pages / pages_per_sheet
        if sheets * pages_per_sheet < pages:
            sheets += 1                 # round up
        if duplex and sheets & 1:
            sheets += 1                 # even number of sheets
        row = 0
        col = 0
        while page_list:
            rc = col  # repeat col
            rr = row  # and row
            page = page_list.pop(0)
            sheet_map[rr][rc].append(page)
            rc += 1
            if rc == cols:
                rc = col
                rr += 1
            if len(sheet_map[row][col]) == sheets:
                col += 1
                if col == cols:
                    col = 0
                    row += 1
        color =  ['color',  (), None]
        cyan = ['cyan', (), None]     # for back of work order or separator
        if front_sheet:
            for row in range(rows):
                for col in range(cols):
                    if row == col == 0:
                        if duplex:
                            sheet_map[row][col] = [cyan] + sheet_map[row][col]
                        sheet_map[row][col] = [front_sheet] + sheet_map[row][col]
                    else:
                        if duplex:
                            sheet_map[row][col] = [cyan] + sheet_map[row][col]
                        sheet_map[row][col] = [color] + sheet_map[row][col]
        # pad with colored sheets
        first = 0
        for row in range(rows):
            for col in range(cols):
                if not first:
                    first = len(sheet_map[row][col])
                elif len(sheet_map[row][col]) < first:
                    while len(sheet_map[row][col]) < first:
                        sheet_map[row][col] += [['color X', (), None]]
        if DEBUG_PAGE_NAMES:
            for row in range(rows):
                for col in range(cols):
                    for sheet in range(len(sheet_map[row][col])):
                        print sheet_map[row][col][sheet][0],
        return sheet_map


    def impose(self, data, filename=None, type=None, output_dir=None):
        ''' Layout and generate press-ready PDFs.
        
        Inputs:
            data = list of data objects specifying what to impose
            type = name of formatting meta data

        Returns:
            PDF file path

        Side Effects:
            generates PDFs
        '''
        try:
            imp = self.build(data, filename, type)
        except Exception, e:
            msg = 'Failed to impose: %s' % e
            self.logger.error(msg)
            raise
        if not imp: 
            return ''
        try:
            if output_dir:
                return self.generate(imp, output_dir)
            return self.generate(imp)
        except Exception, e:
            msg = 'Failed to impose: %s' % e
            self.logger.error(msg)
            raise

    def build(self, data, filename=None, type=None):
        ''' Layout press-ready PDF
        Returns:
            Imp object
        '''
        page_list = []
        sheet_map = []
        workorders = []
        data = map(ImpData, data)
        if not type:    # infer type from 1st data object
            type = data[0].code
            if not type:
                raise ImposeError('Unable to identify product type')
        meta_data = conf.metadata[type]
        if 'mail_merge' in data[0]:
            meta_data['mail-merge'] = data[0]['mail_merge']
        if 'manifest_title' in data[0]:
            meta_data['manifest_title'] = data[0]['manifest_title']
        filename_data = {}
        if 'batched' in data[0] and 'no_manifest' not in data[0]:
            manifest = ['manifest', (), None]
        else:
            manifest = None
        rows, cols = map(int, meta_data['layout'].split('x'))
        total_qty = sum(d.qty for d in data)
        pages_per_side = rows * cols
        for o in data:
            blank = ['blank', (), o]
            color = ['color', (), o]
            cyan = ['cyan', (), None]
            duplex = 'simplex' not in meta_data
            # book content (has a cover) with simplex page siding qualifies
            psuedo_simplex = o.page_siding == 1 and 'cover' in meta_data
            pdf = os.path.join(o.archive_dir, o.pdfname)
            copies = int(o.qty)
            if 'batched' not in o or o.page_list and \
               o.page_list[0] not in ('cover', 'jacket'):
                copies = 1
            for copy in range(1, copies + 1):
                if o.page_list:
                    with_backs = []
                    # add backs to duplex pages
                    for p in o.page_list:
                        p = p.lower()
                        try:
                            p = int(p)
                            odd = p & 1
                        except:
                            with_backs += [p]
                            continue
                        if duplex and not psuedo_simplex:
                            # attach adjacent page
                            if odd:
                                with_backs += [p, p + 1]
                                if p + 1 == o.pages:    
                                    # went too far - back is barcode page
                                    with_backs[-1] = 'barcode'
                            else:   # even
                                with_backs += [p - 1, p]
                        elif psuedo_simplex:
                            # explicitly add blank backs
                            if p == o.pages - 1:
                                with_backs += [p, 'barcode']
                            else:
                                with_backs += [p, 'blank']
                    for p in with_backs:
                        if p in ('cover', 'jacket'):
                            p += ' front'
                            page_list += [[p, (pdf, 1), o]]
                            if o.code == 'M':
                                page_list += [[1, (pdf, 2), o]]
                            elif duplex:
                                p = p.replace('front', 'back')
                                page_list += [[p, (), o]]
                        elif p == 'barcode':
                            barcode = self.addBarcode(o, psuedo_simplex)
                            if len(barcode) == 1 and (o.pages - 1) not in with_backs:
                                # need to add last page
                                barcode = [[o.pages - 1, (pdf, o.pages), o]] + barcode
                            page_list += barcode
                        elif p == 'blank':
                            page_list += [blank]
                        else:
                            print p, pdf, page_list, o.page_list
                            page_list += [[p, (pdf, p + 1), o]]
                else:   # all pages
                    if copy == 1 and 'workorder' in meta_data:
                        uri = '%s%s%s-workorder.pdf' % (genpdf.WORK_ORDER_DIR, o.code, o.order_item_id)
                        work_order = ['work-order', (uri, 1), o]
                        workorders += [work_order]
                        if manifest:
                            page_list += [work_order]
                            if duplex: page_list += [cyan]
                        else:
                            manifest = work_order
                    elif 'batched' in o and o.pages > 2 and \
                         total_qty > pages_per_side:
                        # copy separator
                        page_list += [['color %s - Copy %s' %
                                       (o.order_item_id, copy), (), o]]
                        if duplex: page_list += [cyan]
                    if o.pages > 2:
                        if 'cover' not in meta_data:
                            page_list += [['cover', (pdf, 1), o]]
                        for p in range(1, o.pages):
                            name = p
                            if 'batched' in o:
                                name = 'Copy %s/%s Page %s/%s' % \
                                       (copy, o.qty, p, o.pages)
                            page = [name, (pdf, p + 1), o]
                            page_list += [page]
                            if psuedo_simplex and p < o.pages - 1:
                                page_list += [blank]
                        page_list += self.addBarcode(o, psuedo_simplex)
                    else:   # cards labeled differently
                        name = str(copy)
                        page_list += [[name + ' front', (pdf, 1), o]]
                        if o.pages == 2:
                            page_list += [[name, (pdf, 2), o]]
            filename_data.update(o)
        if not filename:
            filename = '%(code)s-%(order_item_id)s-content-%(qty)s.pdf'
        if 'envelope' in filename:
            sheet_map = o
            num_sheets = o.envelope_qty
        else:
            sheet_map = self.createSheetMap(page_list, rows, cols, 
                                            duplex, manifest)
            num_sheets = len(sheet_map[0][0])
            if duplex:
                num_sheets /= 2
        filename_data['sheets'] = num_sheets
        filename %= filename_data
        filename = filename.replace('--', '-')
        return odict({'sheet_map': sheet_map, 'workorders': workorders, 
                      'meta_data': meta_data, 'filename': filename,
                      'num_sheets': num_sheets})


    def generate(self, data, output_dir=conf.output_dir):
        '''Generates a PDF
        
        Returns:
            filename

        Side Effects:
            creates PDFs sometimes including workorder PDFs
        '''
        fn = os.path.join(output_dir, data.filename)
        if 'envelope' in data.filename:
            data = data.sheet_map
            data.filename = fn
            genpdf.createEnvelopes(data, ENVELOPE_WIDTH, ENVELOPE_HEIGHT)
        else:
            # generate work orders
            color = data.meta_data['color']
            for wo in data.workorders:
                genpdf.createWorkOrder(wo[2], color)
            genpdf.impose(fn, data.sheet_map, data.meta_data)
            # clean up work orders
            try:
                for wo in data.workorders:
                    w = '%s%s%s-workorder.pdf' % (genpdf.WORK_ORDER_DIR, 
                                                  wo[2].code, wo[2].order_item_id)
                    os.remove(w)
            except Exception, e:
                self.logger.warning('Failed to clean up tmp files: %s' % e)
        self.logger.info('Imposed %s' % data.filename)
        return fn
        

    def getNumPressSheets(self, order_item_ids=None, batch=None, component_id=1, qty=None):
        type = None
        if order_item_ids:
            data = []
            for order_item_id in order_item_ids:
                data.append({'order_item_id': order_item_id})
        elif batch:
            data = [{'order_item_id': i.order_item_id, 'qty': i.qty, 'batched': True,
                     'page_list': []}       ##### XXX ####
                     for i in batch.items if i.active]
            if qty:
                data[0]['qty'] = qty
                data[0]['no_manifest'] = True
        # currently only need to distinguish between content and not-content
        if component_id <> 1:
            code = ImpData(data[0]).code
            type = conf.metadata[code].cover
            for d in data:
                d['page_list'] = ['cover']
                d['batched'] = True
        if not data:
            return 0
        imp = self.build(data, type=type)
        return imp.num_sheets
            


