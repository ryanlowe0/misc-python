#!/usr/local/bin/python
# $Id: genpdf.py 6601 2009-12-11 16:06:44Z ryan $

# Ryan Lowe 2006


import sys
import os
import traceback
from pdflib_py import *
from utils import *
from resources import res

conf = res.conf

# global constants
SHEET_WIDTH = 842.4         # max printable area of
SHEET_HEIGHT = 1245.6       # the 864 x 1296 sheet
BLEED = 2.25
FONT_DIR = '%s/fonts' % conf.system.base_dir
IMAGE_DIR = '%s/images' % conf.system.base_dir 
ID_FONT = '%s/Times-Roman' % FONT_DIR
ID_SIZE = 10
BARCODE_FONT = '%s/IDAutomationHC39S' % FONT_DIR
BARCODE_SIZE = 10
LOGO_TEXT = 'mypublisher.com'
LOGO_FONT = '%s/Hermes-Thin' % FONT_DIR
LOGO_SIZE = 12
WORK_ORDER_DIR = '%s/workorders/' % conf.system.base_dir
EMBED_FONTS = True


class GenPDFError(Exception): pass


def init():
    global P
    # initialize PDFlib
    P = PDF_new()
    licenses = conf.imposition.get('licenses')    
    if licenses:
        for l in licenses.split(','):
            PDF_set_parameter(P, 'serial', l)
    PDF_set_parameter(P, 'pdiwarning', 'true')



def countPages(pdf):
    init()
    doc = PDF_open_pdi(P, pdf, '', 0)
    pages = int(PDF_get_pdi_value(P, '/Root/Pages/Count', doc, -1,  0))
    PDF_close_pdi(P, doc)
    return pages


def embedFonts():
    for f in os.listdir(FONT_DIR):
        if not f.lower().endswith('.ttf'): continue
        font = f.lower().rstrip('.ttf')
        PDF_set_parameter(P, 'FontOutline', '%s=%s/%s' % (font, FONT_DIR, f))
        PDF_load_font(P, font, 'unicode', EMBED_FONTS and 'embedding' or '')


def stringWidth(text, font, size):
    if not font.startswith(FONT_DIR):
        font = os.path.join(FONT_DIR, font)
    handle = PDF_findfont(P, font, 'auto', EMBED_FONTS)
    return PDF_stringwidth(P, text, handle, size)


def _color(color):
    cmap = {'black': [0, 0, 0, 1],
            'white': [0, 0, 0, 0],
            'gray20': [.2, .2, .2, .2],
            'red': [0, 1, 1, 0],
            'green': [1, 0, 1, 0],
            'blue': [1, 1, 0, 0],
            'lt-blue': [.5, .5, 0, 0],
            'magenta': [0, 1, 0, 0],
            'yellow': [0, 0, 1, 0],
            'cyan': [1, 0, 0, 0]}
    try:
        return cmap[color]
    except:
        if isinstance(color, list):
            return map(float, color)
        return map(float, color.split(','))
    
    
def _rotation(rotation):
    try:
        rotation = float(rotation)
    except:
        if rotation == 'west':
            rotation = 90.0
        elif rotation == 'north':
            rotation = 0.0
        elif rotation == 'east': 
            rotation = -90.0
        elif rotation == 'south':
            rotation = 180.0
    return rotation
    

def drawLine(x1, y1, x2, y2, color='black', linewidth=0.1):
    PDF_save(P)
    PDF_setcolor(P, 'both', 'cmyk', *_color(color))
    PDF_setlinewidth(P, linewidth)
    PDF_setlinecap(P, 2)
    PDF_moveto(P, x1, y1)
    PDF_lineto(P, x2, y2)
    PDF_stroke(P)
    PDF_restore(P)


def drawRect(x, y, width, height, color, border=0, border_color='black'):
    PDF_save(P)
    PDF_setcolor(P, 'both', 'cmyk', *_color(color))
    PDF_setlinewidth(P, 0.1)
    PDF_rect(P, x, y, width, height)
    PDF_fill(P)
    if border > 0:
        PDF_setcolor(P, 'both', 'cmyk', *_color(border_color))
        PDF_setlinewidth(P, border)
        PDF_rect(P, x, y, width, height)
        PDF_stroke(P)
    PDF_restore(P)
    
    
def drawText(text, font, size, x, y, rotation=0.0, bgcolor=None, color=None):
    rotation = _rotation(rotation)
    text = unicode(str(text), 'latin-1', 'replace')
    if not font.startswith(FONT_DIR): 
        font = os.path.join(FONT_DIR, font)
    PDF_save(P)
    handle = PDF_findfont(P, font, 'auto', EMBED_FONTS)
    PDF_setfont(P, handle, size)
    if rotation <> 0.0:
        PDF_translate(P, x, y)
        x = y = 0.0
        PDF_rotate(P, rotation)
    width = stringWidth(text, font, size)
    PDF_set_text_pos(P, x, y)
    yadjust = hadjust = int(size / 8)
    if font == BARCODE_FONT:
        x -= 2
        width += 4
        yadjust = int(size / 2)
        hadjust = size
    if bgcolor:      # draw a colored box behind text
        drawRect(x, y - yadjust, width, size + hadjust, bgcolor)
    if color:
        PDF_setcolor(P, 'fill', 'cmyk', *_color(color))
    PDF_show(P, text)
    '''
    # block out human-readable text from barcode
    if font == BARCODE_FONT:
        if not bgcolor:
            bgcolor = 'white'
        drawRect(x,  y - yadjust, width, size, bgcolor)
    '''
    PDF_restore(P)


def drawLogo(boxx, boxy, boxw, boxh, rotation=0.0, version='stacked'):
    rotation = _rotation(rotation)
    logo = '%s/mypub_logo_%s.jpg' % (IMAGE_DIR, version)
    image = openImage(P, logo)
    w = PDF_get_value(P, 'imagewidth', image)
    h = PDF_get_value(P, 'imageheight', image)
    resx = PDF_get_value(P, 'resx', image)
    resy = PDF_get_value(P, 'resy', image)
    xpos = boxx + boxw / 2
    ypos = boxy + boxh / 2
    options = '''
    position {50 50}
    rotate %s
    dpi {%s %s}
    ''' % (rotation, resx, resy)
    PDF_fit_image(P, image, xpos, ypos, options)
    PDF_close_image(P, image)
    '''
    mypub_blue = [.32, .1, .08, 0]
    mywidth = stringWidth('my', LOGO_FONT, LOGO_SIZE)
    width = stringWidth('publisher.com', LOGO_FONT, LOGO_SIZE)
    x1 = x2 = boxx + boxw / 2
    y1 = y2 = boxy + boxh / 2
    if rotation == 90:
        y1 -= width / 2 + mywidth
        y2 -= width / 2
    elif rotation == -90:
        y1 += width / 2 + mywidth
        y2 += width / 2
    elif rotation == 180:
        x1 += width / 2 + mywidth
        x2 += width / 2
    else:
        x1 -= width / 2 + mywidth
        x2 -= width / 2
    #drawText('my', LOGO_FONT, LOGO_SIZE, x1, y1, rotation, color=mypub_blue)
    drawText('my', LOGO_FONT, LOGO_SIZE, x1, y1, rotation)
    drawText('publisher.com', LOGO_FONT, LOGO_SIZE, x2, y2, rotation)
    '''


def drawSheetMarks(x, y, sqare_size=3, vertical=False, text=''):
    # color chart
    numcolors = 1
    for hue in range(3, 3 - numcolors, -1):
        for value in range(1, 5):
            color = [0, 0, 0, 0]
            color[hue] = value * .25
            drawRect(x, y, sqare_size, sqare_size, color=color)
            if vertical:
                y += sqare_size
            else:
                x += sqare_size
    # text label
    if text:
        rotation = 0
        if vertical:
            rotation = 90
            y += 2 * sqare_size
        else:
            x += 2 * sqare_size
        drawText(text, 'arial', 12, x, y, rotation)


def drawCropMarks(x, y, width, height, linewidth, length, start, bleed):
    x += bleed
    y += bleed
    width -= 2 * bleed
    height -= 2 * bleed
    x2, y2 = x + width, y + height
    # lower left
    drawLine(x - length, y, x - start, y, linewidth=linewidth)
    drawLine(x, y - start, x, y - length, linewidth=linewidth)
    # lower right
    drawLine(x2 + start, y, x2 + length, y, linewidth=linewidth)
    drawLine(x2, y - start, x2, y - length, linewidth=linewidth)
    # upper left
    drawLine(x - length, y2, x - start, y2, linewidth=linewidth)
    drawLine(x, y2 + start, x, y2 + length, linewidth=linewidth)
    # upper right
    drawLine(x2 + start, y2, x2 + length, y2, linewidth=linewidth)
    drawLine(x2, y2 + start, x2, y2 + length, linewidth=linewidth)


def drawAdhesiveMarks(x, y, width, height, color):
    for i in range(20, 41, 20):
        x1 = x + i
        x2 = x + width - i
        y1 = y + i
        y2 = y + height - i
        drawLine(x1, y1, x2, y1, color, linewidth=9.0)
        drawLine(x1, y1, x1, y2, color, linewidth=9.0)
        drawLine(x1, y2, x2, y2, color, linewidth=9.0)
        drawLine(x2, y1, x2, y2, color, linewidth=9.0)


def openImage(P, filename):
    ' Open image file. Discern type from extension. '
    if filename.endswith('.jpg'):
        typ = 'jpeg'
    elif filename.endswith('.gif'):
        typ = 'gif'
    elif filename.endswith('.tif'):
        typ = 'tiff'
    elif filename.endswith('.png'):
        typ = 'png'
    else:
        raise TypeError, 'Unkown file type'
    try:
        return PDF_open_image_file(P, typ, filename, '', 0)
    except:
        return -1


def drawManifest(x, y, width, height, sheet_map, title=None):
    data = {}
    rows = len(sheet_map)
    cols = len(sheet_map[0])
    sheets = len(sheet_map[0][0])    
    for sheet in range(sheets):
        for row in range(rows):
            for col in range(cols):
                try:
                    page, src, o = sheet_map[row][col][sheet]
                    if o.order_item_id not in data:
                        data[o.order_item_id] = o
                except:
                    continue
    if width > height:
        orientation = 'west'
        xpos, ypos = x + 20, y + 20
    else:
        orientation = 'north'
        xpos, ypos = x + 10, y + height - 40
    data = data.items()
    data.sort()
    if title:
        w = stringWidth(title, 'Times-Roman', 10) + 5
        w2 = stringWidth(title, BARCODE_FONT, BARCODE_SIZE) + 5
        if orientation == 'west':
            drawText(title, 'Times-Roman', 10, xpos, 
                     ypos + height / 2 - (w + w2) / 2, orientation)
            title = '*%s*' % title.replace(' ', '')
            drawText(title, BARCODE_FONT, BARCODE_SIZE, 
                     xpos, ypos + height / 2 - w2 / 2 + w / 2, orientation)
            drawLine(xpos + 15, ypos, xpos + 15, ypos + height - 40)
            xpos += 40
        else:
            drawText(title, 'Times-Roman', 10, xpos + width / 2 - (w + w2) / 2, 
                     ypos, orientation)
            title = '*%s*' % title.replace(' ', '')
            drawText(title, BARCODE_FONT, BARCODE_SIZE, 
                     xpos + width / 2 - w2 / 2 + w / 2, ypos, orientation)
            drawLine(xpos + 30, ypos - 15, xpos + width - 40, ypos - 15)
            ypos -= 40
    startx, starty = xpos, ypos
    for order_item_id, o in data:
        if int(order_item_id) < 0:
            continue
        text = '%s - Qty %s Pgs %s' % (order_item_id, o.qty, o.pages)
        bar_text = '*%s*' % order_item_id
        w = stringWidth(text, 'Times-Roman', 9)
        w2 = stringWidth(bar_text, BARCODE_FONT, BARCODE_SIZE)
        drawText(text, 'Times-Roman', 9, xpos, ypos, orientation)
        bar_x, bar_y = xpos, ypos
        if orientation == 'west':
            bar_y += w + 5
        else:
            bar_x += w + 5
        drawText(bar_text, BARCODE_FONT, BARCODE_SIZE, 
                 bar_x, bar_y, orientation)
        if orientation == 'west':
            xpos += 40
            if xpos > width - 40:
                xpos = startx
                ypos += w + w2 + 20
        else:
            ypos -= 40
            if ypos < y + 40:
                ypos = starty
                xpos += w + w2 + 20
        

def createEnvelopes(data, width, height):
    init()
    PDF_open_file(P, data['filename'])
    if 'return_address' in data:
        data['address'] = unicode(data['return_address'], 'latin-1', 'replace')
    for p in range(data['envelope_qty']):
        PDF_begin_page(P, width, height)
        font = PDF_findfont(P, '%s/helvetica' % FONT_DIR, 'auto', EMBED_FONTS)
        PDF_setfont(P, font, 10)
        PDF_set_value(P, 'leading', 12)
        w = 300
        h = (data['address'].count('\n') + 1) * 12
        HALF_FLAP_HEIGHT = 88
        PDF_show_boxed(P, data['address'], width / 2 - w / 2, 
                       height - h / 2 - HALF_FLAP_HEIGHT, 
                       w, h, 'center', '')
        PDF_end_page(P)
    PDF_close(P)
    return data['filename']


def createWorkOrder(order_data, color):
    ' Creates a workorder PDF'
    init()
    
    o = order_data
    filename = '%s%s%s-workorder.pdf' % (WORK_ORDER_DIR, o.code, o.order_item_id)
    w, h = 1053.36, 813.6
    
    pdf = PDF_open_file(P, filename)
    PDF_begin_page(P, w, h)
                
    # draw colored border
    drawRect(0, 0, 50, h, color)
    drawRect(0, 0, w, 50, color)
    drawRect(0, h - 50, w, 50, color)
    drawRect(w - 50, 0, 50, h, color)
    # draw letter code symbol
    x, y = 100, h - 275
    drawRect(x, y, 150, 150, color, 3, 'white' if color == 'blue' else 'black')
    str_width = stringWidth(o.code, 'arialbd', 120)
    drawText(o.code, 'arialbd', 120, x + 75 - str_width / 2, y + 35, 
             color='white' if color == 'blue' else 'black')
    # date
    drawText(o.date, 'arialbd', 28, x, y + 180)
    # draw product description
    handle = PDF_findfont(P, '%s/arial' % FONT_DIR, 'auto', EMBED_FONTS)
    PDF_setfont(P, handle, 18)
    PDF_show_boxed(P, o.product, x, y - 220, 150, 200, 'center', '')
    # place flag image
    flag = '%s/%s-flag.tif' % (IMAGE_DIR, o.flag)
    image = openImage(P, flag)
    PDF_place_image(P, image, 100, 100, .25)
    PDF_close_image(P, image)
    # draw barcode / order_item_id
    drawText('*%s*' % o.order_item_id, BARCODE_FONT, 24, 125, 430, 'east', 'white')
    drawText(o.order_item_id, 'arialbd', 28, 200, 400, 'east', 'white')
    # draw comments section
    x, y, w2, h2 = 300, 250, 370, 270
    drawRect(x, y, w2, h2, [0, 0, 0, .05])
    handle = PDF_findfont(P, '%s/courierbd' % FONT_DIR, 'auto', EMBED_FONTS)
    PDF_setfont(P, handle, 26)
    text = o.comments or ''
    PDF_show_boxed(P, text, x + 20, y + 20, w2 - 40, h2 - 40, 'center', '')
    # place cover and page 1 thumbs
    pdfname = o.archive_dir + os.sep + o.pdfname
    doc_handle = PDF_open_pdi(P, pdfname, '', 0)
    options = 'position 0 fitmethod meet boxsize {%f %f}' % (300, 300)
    if o.show_cover:
        page_handle = PDF_open_pdi_page(P, doc_handle, 1, '')
        if PDF_get_pdi_value(P, 'width', doc_handle, page_handle, 0) < \
           PDF_get_pdi_value(P, 'height', doc_handle, page_handle, 0):
            if o.code == 'L':
                options += ' orientate west'
            else:
                options += ' orientate east'
        PDF_fit_pdi_page(P, page_handle, w - 360, h - 340, options)
        PDF_close_pdi_page(P, page_handle)
    page_handle = PDF_open_pdi_page(P, doc_handle, 2, '')
    PDF_fit_pdi_page(P, page_handle, w - 360, h - 650, options)
    PDF_close_pdi(P, doc_handle)                    
    #drawRect(w - 360, h - 360, 300, 300, [0, 0, 0, .5])
    #drawRect(w - 360, h - 660, 300, 300, [0, 0, 1, .5])
    # draw shipping info
    drawText('Address', 'arialbd', 20, 300, 200)
    drawText(o.address, 'arial', 18, 300, 180)
    drawText('Method', 'arialbd', 20, 300, 120)
    drawText(o.method, 'arial', 18, 300, 100)
    drawText('Order Number', 'arialbd', 20, w - 350, 120)
    drawText(o.order_number, 'arial', 18, w - 350, 100)
    # draw cover, qty, pages
    if o.cover_swatch_file:
        swatch = '%s/%s' % (IMAGE_DIR, o.cover_swatch_file)
        image = openImage(P, swatch)
        if image <> -1:
            PDF_place_image(P, image, 560, h - 160, .5)
            PDF_close_image(P, image)
    text = 'Cover'
    if o.code in 'KL': 
        text = 'Envelope Bundles'
        if o.print_return_address:
            drawText('Return Address', 'arialbd', 20, 510, h - 100)
            for i, line in enumerate(o.return_address.split('\n')):
                drawText(line, 'courier', 14, 510, h - i * 16 - 130)
    if o.cover:
        drawText(text, 'arialbd', 20, 300, h - 100)
        handle = PDF_findfont(P, '%s/arial' % FONT_DIR, 'auto', EMBED_FONTS)
        PDF_setfont(P, handle, 28)
        PDF_show_boxed(P, o.cover, 300, h - 310, 250, 200, 'left', '')
    drawText('Quantity', 'arialbd', 20, 300, h - 220)
    drawText(o.order_qty, 'arialbd', 28, 300, h - 260)
    drawText('Pages', 'arialbd', 20, 430, h - 220)
    pages = int(o.pages)
    if 'simplex' in o.product.lower():
        pages *= 2
    drawText(str(pages), 'arialbd', 28, 430, h - 260)
    if o.staple:
        drawText('Staple', 'arialbd', 20, 560, h - 220)
        drawText(o.staple, 'arialbd', 28, 560, h - 260)
    # close up shop
    PDF_end_page(P)
    PDF_close(P)
    return filename
   


def impose(filename, sheet_map, meta_data):
    init()

    mail_merge = []
    if 'mail-merge' in meta_data:
        mail_merge = meta_data['mail-merge']

    if 'pdf-size' in meta_data:
        sheet_width, sheet_height = map(float, meta_data['pdf-size'].split(','))
    else:
        sheet_width, sheet_height = SHEET_WIDTH, SHEET_HEIGHT

    retcode = PDF_open_file(P, filename)
    if retcode == -1:
        raise GenPDFError(PDF_get_errmsg(P))
    #embedFonts()
    pdis = {}
    rows = len(sheet_map)
    cols = len(sheet_map[0])
    sheets = len(sheet_map[0][0])        
    next_handle = 0
    width, height = map(float, meta_data['size'].split(','))
    if 'media-box' in meta_data:
        pos, size = meta_data['media-box'].split(' ')
        mediax, mediay = map(float, pos.split(','))
        width, height = map(float, size.split('x'))
    sheet_orient = content_orient = meta_data['orientation']
    if 'content-orientation' in meta_data:
        content_orient = meta_data['content-orientation']
    binding_side_id = 'id-side' not in meta_data or meta_data['id-side'] == 'binding'
    if 'id-gap' in meta_data:
        id_gap = float(meta_data['id-gap'])
    elif not binding_side_id:
        id_gap = 57.6            # identifier outside page: need larger gap
    else:
        id_gap = 1
    if 'gap' in meta_data:      # gap between adjacent pages on sheet
        gap = float(meta_data['gap'])
    else:
        gap = 1
    if sheet_orient == 'west' and width > height:
        width, height = height, width
        hgap = id_gap
        wgap = gap
        if 'spaced' in meta_data:
            wgap = id_gap
    else:
        wgap = id_gap
        hgap = gap
        if 'spaced' in meta_data:
            hgap = id_gap
    gutterwidth = (sheet_width - width * cols - wgap * (cols - 1)) / 2
    gutterheight = (sheet_height - height * rows - hgap * (rows - 1)) / 2
    for sheet in range(sheets):
        crops = []
        isback = 'simplex' not in meta_data and sheet & 1   # sheet back?
        flippage = isback
        if 'no-flip' in meta_data: flippage = False
        #isback = 0                 # duplex deluxe reorders < 2006-05-08
        #flippage = sheet & 1 <> 0  # duplex deluxe reorders < 2006-05-08
        try:
            PDF_begin_page(P, sheet_width, sheet_height)
        except Exception, e:
            msg = "Unable to Create PDF page, %s: %s" % (filename, e)
            raise GenPDFError (msg)
        if flippage:
            PDF_translate(P, sheet_width, sheet_height)
            PDF_rotate(P, 180)
        if 'cover_shadow' in meta_data:
            h, w = map(float, conf.imposition.metadata
                [meta_data['cover']]['size'].split(','))
            #xpos = (sheet_width - w) / 2
            #ypos = (sheet_height - h) / 2
            xpos, ypos = 0, 34.92
            drawRect(xpos, ypos, 2 * w + wgap, h, meta_data['cover_shadow'])
        drew_sheet_marks = 'no-chart' in meta_data
        vert_chart = meta_data.get('chart-orient') <> 'horiz'
        for row in range(rows):
            for col in range(cols):
                try:
                    page, src, o = sheet_map[row][col][sheet]
                    page = str(page)
                except:
                    continue
                # override based on order data
                if o and o.orientation == 'vertical': 
                    content_orient = 'north'
                elif o and o.orientation == 'horizontal':
                    content_orient = 'west'
                logo_version = meta_data.get('logo-version', 'stacked')
                # compute (x, y) of page from layout, location, size, and flip
                y = sheet_height - gutterheight - (height + hgap) * (row + 1) + hgap
                # undo flip-page for barcode/logo page of calendars
                if 'no-flip-last' in meta_data and 'logo' in page:
                    PDF_translate(P, sheet_width, sheet_height)
                    PDF_rotate(P, 180)
                    flippage = False
                if flippage:
                    x = sheet_width - gutterwidth - (width + wgap) * (col + 1) + wgap
                else:
                    x = gutterwidth + col * (width + wgap)
                # blank out field prior to laying shadow rectangle
                if 'cover_shadow' in meta_data:
                    drawRect(x, y, width, height, 'white')
                # place page
                if src:
                    if src[0].endswith('.pdf'):
                        pdi, src_page = src
                        if pdi not in pdis:
                            pdis[pdi] = next_handle
                            next_handle += 1
                            # open pdi
                            doc_handle = PDF_open_pdi(P, pdi, '', 0)
                        doc_handle = pdis[pdi]
                        try:
                            page_handle = PDF_open_pdi_page(P, doc_handle, src_page, '')
                        except:
                            traceback.print_exc()
                            PDF_end_page(P)
                            PDF_close(P)
                            raise
                        source_width = PDF_get_pdi_value(P, 'width', doc_handle, page_handle, 0)
                        source_height = PDF_get_pdi_value(P, 'height', doc_handle, page_handle, 0)
                    else:
                        image = openImage(P, src[0])
                        source_width = PDF_get_value(P, 'imagewidth', image)
                        source_height = PDF_get_value(P, 'imageheight', image)
                    if not drew_sheet_marks and page <> 'cyan':
                        s, s2 = sheet, sheets
                        if 'simplex' not in meta_data:
                            s /= 2
                            s2 /= 2
                        text = '%s of %s' % (s + 1, s2)
                        xpos = ypos = 10
                        if 'sheet-offset' in meta_data:
                            offset = meta_data['sheet-offset'].split(',')
                            xpos += int(offset[0])
                            ypos += int(offset[1])
                        drawSheetMarks(xpos, ypos, vertical=vert_chart, text=text)
                        drew_sheet_marks = True
                    # use dimensions to distinguish old pocket books
                    source_wider = source_width > source_height   
                    wider = width > height
                    in_ratio = [source_width, source_height]
                    in_ratio.sort()
                    out_ratio = [width, height]
                    out_ratio.sort()
                    yoff = 0
                    overlay = ''
                    if in_ratio[1] < 2 * in_ratio[0] and out_ratio[1] > 2 * out_ratio[0]:
                        # cover image only (old pocket books)
                        options = '''
                        position 50
                        fitmethod meet
                        boxsize {%f %f}
                        ''' % (width, height / 2)
                        yoff = height / 2 + 18.0        # spine allowance magic number
                        overlay = '%s/pocketbook_cover.png' % IMAGE_DIR
                    elif 'media-box' in meta_data:
                        # account for rotation
                        if (width < height and source_wider or 
                            width > height and not source_wider):
                            source_width, source_height = source_height, source_width
                        # die-cut only? center in media box
                        if source_width < width and source_height < height:
                            options = '''
                            position 50
                            boxsize {%f %f}
                            ''' % (width, height)
                        else:
                            options = '''
                            position {%f %f}
                            fitmethod clip
                            boxsize {%f %f}
                            ''' % (mediax, mediay, width, height)
                    else:
                        options = '''
                        position 0 
                        fitmethod entire
                        boxsize {%f %f}
                        ''' % (width, height)
                    # rotate?
                    if sheet_orient == 'west' and source_wider:
                        options += ' orientate west'
                    elif sheet_orient == 'north' and not source_wider:
                        options += ' orientate east'
                    # undo flip for west oriented content
                    if (sheet_orient == 'west' and content_orient == 'west'
                        and isback and 'no-flip' not in meta_data and
                        'no-flip-last' not in meta_data):
                        if 'reverse-cols' not in meta_data or not col & 1:
                            options += ' orientate east'
                            options = options.replace(' orientate west', '')
                    elif 'reverse-cols' in meta_data and col & 1:
                        options += ' orientate east'
                        options = options.replace(' orientate west', '')
                    if src[0].endswith('.pdf'):
                        PDF_fit_pdi_page(P, page_handle, x, y + yoff, options)
                        if overlay:
                            image = openImage(P, overlay)
                            PDF_fit_image(P, image, x, y + yoff, options)
                            PDF_close_image(P, image)
                        PDF_close_pdi_page(P, page_handle)
                    else:
                        PDF_fit_image(P, image, x, y + yoff, options)
                if not drew_sheet_marks and page <> 'cyan':
                    s, s2 = sheet, sheets
                    if 'simplex' not in meta_data:
                        s /= 2
                        s2 /= 2
                    text = '%s of %s' % (s + 1, s2)
                    xpos = ypos = 10
                    if 'sheet-offset' in meta_data:
                        offset = meta_data['sheet-offset'].split(',')
                        xpos += int(offset[0])
                        ypos += int(offset[1])
                    drawSheetMarks(xpos, ypos, vertical=vert_chart, text=text)
                    drew_sheet_marks = True
                # draw color-coded separator page
                if page.startswith('color'):
                    drawRect(x, y, width, height, meta_data['color'])
                    text = page.lstrip('color').strip()
                    if not text:
                        num = row * cols + col      # row-first ordering
                        #num = col * rows + row     # col-first ordering
                        text = str(num + 1)
                    str_width = stringWidth(text, 'Times-Roman', 36)
                    orient = sheet_orient
                    xpos = x + width / 2
                    ypos = y + height / 2
                    if orient == 'west':
                        xpos += 18
                        ypos -= str_width / 2
                    else:
                        xpos -= str_width / 2
                        ypos -= 18
                    if 'reverse-cols' in meta_data and col & 1 and orient == 'west':
                        orient = 'east'
                        ypos += str_width
                    drawText(text, 'Times-Roman', 36, xpos, ypos, orient)
                # add crop marks
                ignore = 'blank', 'cyan', 'cover back'
                if none_in(ignore, page):
                    if 'crop-size' in meta_data:
                        linewidth, length, start, bleed = map(float, meta_data['crop-size'].split(','))
                    else:
                        linewidth, length, start, bleed = 0.3, 4, 2, BLEED
                    if 'no-crops' not in meta_data:
                        crops.append([x, y, width, height, linewidth, 
                                      length, start, bleed])
                    if 'pre-trim-crops' in meta_data:
                        xoff, yoff = map(float, meta_data['pre-trim-crops'].split(','))
                        crops.append([x - xoff, y - yoff, width + 2 * xoff, 
                                      height + 2 * yoff, linewidth, length, 
                                      start, bleed])
                # draw adhesive markers
                if 'adhesive' in meta_data and page == 'cover':
                    drawAdhesiveMarks(x, y, width, height, meta_data['color'])
                # place barcode/logo
                if 'barcode' in page:
                    xpos = x + 30
                    ypos = y + 30
                    if content_orient == 'west':
                        xpos = x + width - 30
                    if 'barcode-size' in meta_data:
                        size = float(meta_data['barcode-size'])
                    else:
                        size = BARCODE_SIZE
                    drawText('*%s*' % o.order_item_id, BARCODE_FONT, size, 
                             xpos, ypos, content_orient, 'white')
                if 'logo' in page:
                    drawLogo(x, y, width, height, content_orient, logo_version)
                if 'barcode' in meta_data:
                    if 'front' in meta_data['barcode'] and 'front' in page:
                        if ',' in meta_data['barcode']:
                            coords = meta_data['barcode'].split(' ')[-1]
                            xpos, ypos = map(float, coords.split(','))
                            xpos += x
                            ypos += y
                        else:
                            xpos = x + width - 150
                            #xpos = x + width - 135
                            ypos = y + height / 2
                            if content_orient == 'west':
                                xpos = x + width / 2
                                ypos = y + 215
                        rotation = sheet_orient
                        if 'vertical' in meta_data['barcode']:
                            if content_orient == 'west':
                                rotation = 0.0
                                #xpos2 = xpos + 80
                                #ypos2 = ypos
                            else:
                                rotation = 90.0
                                #xpos2 = xpos
                                #ypos2 = ypos + 80
                        barcode_text = str(o.order_item_id) + o.barcode_suffix
                        if 'barcode-size' in meta_data:
                            size = float(meta_data['barcode-size'])
                        else:
                            size = BARCODE_SIZE
                        drawText('*%s*' % barcode_text, BARCODE_FONT, size, 
                                 xpos, ypos, rotation, 'white')
                        #drawText(order_item_id, 'Times-Roman', 14, xpos2, ypos2, 
                        #         rotation, 'white')
                    elif 'back' in meta_data['barcode'] and 'back' in page:
                        if ',' in meta_data['barcode']:
                            coords = meta_data['barcode'].split(' ')[-1]
                            xpos, ypos = map(float, coords.split(','))
                            xpos += x
                            ypos += y
                        else:
                            xpos = x + width - 20
                            ypos = y + height - 110
                        if 'barcode-size' in meta_data:
                            size = float(meta_data['barcode-size'])
                        else:
                            size = BARCODE_SIZE
                        orient = sheet_orient
                        if 'reverse-cols' in meta_data and col & 1 and \
                           orient == 'west':
                            # special case only tested on pocket books
                            orient = 'east'
                            xpos = 2 * x + width - xpos
                            ypos = 2 * y + height - ypos
                        drawText('*%s*' % o.order_item_id, BARCODE_FONT, size, 
                                 xpos, ypos, orient, 'white')
                        if 'back' in meta_data.get('logo'):
                            w, h = width, height
                            xpos, ypos = x, y
                            if content_orient == 'west':
                                h /= 2
                                ypos += h - 36      # spine offset magic number
                                if 'reverse-cols' in meta_data and col & 1:
                                    ypos -= h - 72
                            else:
                                w /= 2
                                xpos += w - 36      # spine offset magic number
                            drawLogo(xpos, ypos, w, h, orient, logo_version)
                if mail_merge:
                    try:
                        #int(page)  # just backs

                        # address
                        #text = '%s\n%s\n%s, %s %s' % tuple(mail_merge.pop(0)[2:7])
                        # coupon code
                        text = mail_merge.pop(0)[0]
                        handle = PDF_findfont(P, '%s/arial' % FONT_DIR, 'auto', EMBED_FONTS)
                        PDF_save(P)
                        xpos = x + width / 2
                        ypos = y + height / 2
                        PDF_translate(P, xpos, ypos)
                        PDF_rotate(P, -90)
                        PDF_setfont(P, handle, 15.6)
                        #print 'x y', x, y, 'pos', xpos, ypos, 'w h', width / 2, height / 2
                        PDF_show_boxed(P, text, -220, -313, 155, 400, 'left', '')
                        PDF_restore(P)
                    except Exception, e:
                        #print e
                        pass
                # this currently only applies to greeting cards and may
                # not generalize without some tweaking
                if ('front' in page and 'logo' in meta_data and 
                    'front' in meta_data['logo']):
                    w, h = width, height
                    xpos, ypos = x, y
                    orient = content_orient
                    if orient == 'north':
                        orient = 'south'
                    w /= 2
                    xpos += w
                    drawLogo(xpos, ypos, w, h, orient, logo_version)
                # this currently only applies to postcards and may
                # not generalize without some tweaking
                ignore = ('front', 'blank', 'work-order', 'manifest', 
                          'color', 'cyan', 'cover back')
                if none_in(ignore, page) and 'logo' in meta_data and \
                   'back' in meta_data['logo']:
                    w, h = width, height
                    xpos, ypos = x, y
                    orient = content_orient
                    if orient == 'north':
                        ypos -= h / 2 - 30
                    else:
                        orient = 'east'
                        xpos -= w / 2 - 30
                    drawLogo(xpos, ypos, w, h, orient, logo_version)
                if page == 'manifest':
                    title = meta_data.get('manifest_title')
                    drawManifest(x, y, width, height, sheet_map, title)
                elif page == 'cyan':
                    w, h = width, height
                    xoff = yoff = 0
                    if not binding_side_id:
                        if sheet_orient == 'west':
                            yoff = 50
                        else:   # north
                            xoff = 50
                    if 'no-extend-separator' in meta_data:
                        drawRect(x, y, w, h, 'cyan')
                    else:
                        drawRect(x - xoff, y - yoff, w + xoff, h + yoff, 'cyan')
                if 'center-lines' in meta_data and (sheet == 0 or 
                   any_in(('horiz', 'vert'), meta_data['center-lines'])):
                    meta_data['center-lines'] = str(meta_data['center-lines'])
                    try:
                        xoff, yoff = map(int, meta_data['center-lines'].split(','))
                    except:
                        xoff = yoff = 0
                    lwidth = float(meta_data.get('center-lines-size', .1))
                    import re
                    length = re.sub('[^\d.]', '', meta_data['center-lines'])
                    if length:
                        length = float(length)
                    else:
                        length = 50
                    if rows > 1 or 'horiz' in meta_data['center-lines']:
                        # horizontal lines
                        xpos = sheet_width
                        ypos = sheet_height / 2 + yoff
                        drawLine(0, ypos, length, ypos, linewidth=lwidth)
                        if 'reverse-cols' in meta_data:
                            ypos = sheet_height / 2 - yoff
                        drawLine(xpos - length, ypos, xpos, ypos, linewidth=lwidth)
                    if cols > 1 or 'vert' in meta_data['center-lines']:
                        # vertical lines
                        xpos = sheet_width / 2 + xoff
                        ypos = sheet_height
                        drawLine(xpos, 0, xpos, length, linewidth=lwidth)
                        drawLine(xpos, ypos - length, xpos, ypos, linewidth=lwidth)

                
                if 'extra-text' in meta_data and sheet == 0:
                    if 'outer-centers' in meta_data['extra-text']:
                        text = meta_data['extra-text']['outer-centers']
                        str_width = stringWidth(text, 'arial', 16)
                        xpos = x + width / 2 - str_width / 2
                        if row == 0:
                            ypos = y + height# + 16
                        else:
                            ypos = y - 16
                        drawText(text, 'arialbd', 16, xpos, ypos)

                # these pages dont get an identifier
                no_id = 'blank', 'work-order', 'manifest', 'color','cyan'
                if any_in(no_id, page) or 'id-text' not in meta_data or \
                   not meta_data['id-text']:
                    continue
                # draw identifier
                id_text = meta_data['id-text']
                page = page.title()
                pages = o.pages - 1
                qty = o.qty
                cover = o.cover
                order_item_id = o.order_item_id
                for rep in ['order_item_id', 'page', 'pages', 'qty', 'cover']:
                    id_text = id_text.replace('<%s>' % rep, str(eval(rep)))
                handle = PDF_findfont(P, ID_FONT, 'auto', EMBED_FONTS)
                if 'id-size' in meta_data:
                    id_size = float(meta_data['id-size'])
                else:
                    id_size = ID_SIZE
                str_width = stringWidth(id_text, 'arial', id_size)
                # position identifier text
                xpos, ypos = x, y
                if 'id-pos' in meta_data:
                    rotation = meta_data['id-orient']
                    xpos, ypos = map(float, meta_data['id-pos'].split(','))
                elif sheet_orient == 'west':
                    if binding_side_id:
                        if isback:
                            rotation = 'north'
                            xpos += width / 2 - str_width / 2
                            ypos += height - id_size - 2
                        else:
                            rotation = 'south'
                            xpos += width / 2 + str_width / 2
                            ypos += id_size + 2
                    else:
                        if 'reverse-cols' in meta_data and col & 1:
                            rotation = 'north'
                            xpos += width / 2 - str_width / 2
                            ypos -= id_size
                        else:
                            rotation = 'south'
                            xpos += width / 2 + str_width / 2
                            ypos += height + id_size
                elif sheet_orient == 'north':
                    if binding_side_id:
                        if isback:
                            rotation = 'east'
                            xpos += width - id_size - 2
                            ypos += height / 2 + str_width / 2
                        else:
                            rotation = 'west'
                            xpos += id_size + 2
                            ypos += height / 2 - str_width / 2
                    else:
                        if isback:
                            rotation = 'east'
                            xpos -= id_size
                            ypos += height / 2 + str_width / 2
                        else:
                            rotation = 'west'
                            xpos += width + id_size
                            ypos += height / 2 - str_width / 2
                drawText(id_text, ID_FONT, id_size, xpos, ypos, rotation, 'white')
        for c in crops:
            drawCropMarks(*c)
        PDF_end_page(P)

        
    # close pdi's 
    for handle in range(len(pdis)):
        PDF_close_pdi(P, handle)
    PDF_close(P)
    PDF_delete(P)
    
    # check that valid pdf was created
    #assert 'PDF document' in os.popen('file %s' % filename).read()
    
    return filename
    
