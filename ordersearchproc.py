# -*- coding: utf-8 -*-
import os
import re
from math import ceil
from decimal import Decimal
from sqlalchemy import desc
from sqlalchemy.sql import between, or_, alias
from sqlalchemy.orm import aliased, eagerload
from plant.dbengine import transactional
from plant.smartdate import Date
from datetime import datetime
from plant.controllers.orders import Orders
from plant.controllers.batches import Batches
from plant.controllers.payments import Invoices
from plant.model import Address, Association, Coupon, Customer, Email, \
                        ExchangeRate, GiftCertificate, Invoice2, Order, \
                        OrderDiscount, OrderItem, OrderItemFeature, Payment, \
                        PaymentTransaction, Product, ProductItem, ProductType, \
                        Promotion, Refund, ShippingEndicia, \
                        ShippingEndiciaHistory, ShippingFedex, ShippingMethod, \
                        SoftwareVersion, State, WorkflowItem
from web.reportutils import parseOrderIds
from reporting import formatDollars, until, FEDEX, USPS, ROYAL, UPS

BillAddress = aliased(Address)
ShipAddress = aliased(Address)

class RptOrder(object):
    """Place to assign order related data representing an order to the report.
    Useful as opposed to passing nearly a hundred fields around in arg lists."""
    def assignFields(self, order_list):
        """Assign the fields collected to the order dict expected by the report
        and append that to the list passed in."""
        order_list.append(
            {"foid": self.order.order_id,
             "vip": self.vip,
             "book_id": self.product_item_id,
             "batch_id": self.batch_id,
             "order_number": self.order_number,
             "orig_order_num": self.original_order_number,
             "order_state": self.order_state,
             "batch_state": self.batch_state,
             "mfg_state": self.mfg_state,
             "show_mfg_state": self.show_mfg_state,
             "show_batch_state": self.show_batch_state,
             "before_coupon": "%0.2f" % self.gross,
             "gross": "%0.2f" % self.net, # yes it seems wrong but it's not
             "tax": "%0.2f" % self.tax,
             "discount": "%0.2f" % (self.gross - self.net),
             "order_total": "%0.2f" % self.order_total,
             "cc_paid": "%0.2f" % self.cc_paid,
             "order_date": self.order_date,
             "date": self.date,
             "ship_date": self.ship_date,
             "ship_dates": self.ship_dates,
             "partner": self.partner,
             "promo": self.promo,
             "coupon_code": self.coupon_code,
             "assoc": self.assoc,
             "shipping": "%0.2f" % self.shipping,
             "fee": "%0.2f" % self.fee,
             "ship_to": self.ship_to,
             "ship_address": self.ship_address,
             "ship_city": self.ship_city,
             "ship_state": self.ship_state,
             "ship_zip": self.ship_zip,
             "ship_country": self.ship_country,
             "ship_phone": self.ship_phone,
             "method": self.method,
             "method_link": self.method_link,
             "method_title": self.method_title,
             "bill_to": self.bill_to,
             "bill_address": self.bill_address,
             "bill_city": self.bill_city,
             "bill_state": self.bill_state,
             "bill_zip": self.bill_zip,
             "bill_country": self.bill_country,
             "bill_phone": self.bill_phone,
             "bill_email": self.bill_email,
             "product": self.product, 
             "simplex_duplex": self.simplex_duplex, 
             "qty": self.qty, 
             "pages": self.pages, 
             "cover_color": until(self.cover_color, "_"),
             "leather": self.leather,
             "orientation": self.orientation,
             "tracking_number": self.tracking_number,
             "tracking_numbers": self.tracking_numbers,
             "custom_info": self.theme,
             "currency": self.currency,
             "comments": self.comments,
             "verisign": self.dc_transaction_number,
             "dc_transaction_number": self.dc_transaction_number,
             "charge_date": self.charge_date,
             "cover_thumb": self.cover_thumb,
             "pdf": self.pdf_url,
             "dime_url": self.dime_url,
             "client": self.version,            
             "payment_processor": self.payment_processor,
             "user_id": self.order.customer.username,
             "refunds": self.refunds,
             "product_group": self.product_group,
             "return_address": self.return_address,
             "recipient": self.recipient,
             "recipient_email": self.recipient_email,
             "redeemed_orders": self.redeemed_orders,
             "gc_code": self.gc_code,
             "gc_amount": "%0.2f" % self.gc_amount,
             "gc_amount_redeemed": "%0.2f" % self.gc_amount_redeemed,
             "gc_balance": "%0.2f" % self.gc_balance,
             "gift_certs": self.gift_certs})

class OrderSearchProc(object):
    """Provides order search data."""

    def __init__(self):
        self.orders = Orders()
        self.batches = Batches()
        self.invoices = Invoices()
        
    def _filterByDate(self, q, start_date, end_date, params):
        if start_date and end_date:
            s_date = Date(start_date)
            e_date = Date(end_date) + 1
            if params.date_type == "order_date":
                q = q.filter((Order.order_date >= s_date) &
                             (Order.order_date < e_date))
            else:
                q = q.filter((Invoice2.ship_date >= s_date) &
                             (Invoice2.ship_date < e_date))
        elif start_date:
            s_date = Date(start_date)            
            if params.data_type == "order_date":
                q = q.filter(Order.order_date >= s_date) 
            else:
                q = q.filter(Invoice2.ship_date >= s_date) 
        elif end_date:
            e_date = Date(end_date)            
            if params.data_type == "order_date":
                q = q.filter(Order.order_date < e_date)
            else:
                q = q.filter(Invoice2.ship_date < e_date)                 
        return q
    
    def _filterByShipCountry(self, q, params):                        
        if not params.ship_country:
            return q

        ship_country = params.ship_country

        if not hasattr(ship_country, '__iter__'):
            ship_country = [ship_country]

        ship_country = [c for c in ship_country if c <> "*"]

        if ship_country and "*" in params.ship_country:
            q = q.filter((ShipAddress.country.in_(ship_country)) |
                         (~ShipAddress.country.in_(["US", "CA"])))
        elif ship_country:
            q = q.filter(ShipAddress.country.in_(ship_country))
        elif "*" in params.ship_country:
            q = q.filter(~ShipAddress.country.in_(["US", "CA"]))
        return q

    def _filterByProduct(self, q, params):
        if hasattr(params.skus, '__iter__'):
            skus = []
            for s in params.skus:
                skus += [x for x in s.split(',')]
        else:
            skus = [x for x in params.skus.split(',')]

        if skus:
            criteria = []
        
            if ("BOOKMAKER_HCBOOK_IC_S" in skus or
                "BOOKMAKER_HCBOOK_IC_D" in skus or "STD_PDFBOOK" in skus):
                # Classic Die Cut
                criteria.append(((OrderItem.product_id == 2) &
                                 (OrderItemFeature.cover_type_id == 1)))

            if ("BOOKMAKER_HCBOOK_PJ_S" in skus or
                "BOOKMAKER_HCBOOK_PJ_D" in skus):
                #Classic Jacketed
                criteria.append(((OrderItem.product_id == 2) &
                                 (OrderItemFeature.cover_type_id == 2)))
                
            if ("BOOKMAKER_HCDELUXE_IC_S" in skus or
                "BOOKMAKER_HCDELUXE_IC_D" in skus or "STD_PDFDELUXE" in skus):
                # Deluxe Die Cut
                criteria.append(((OrderItem.product_id == 3) &
                                 (OrderItemFeature.cover_type_id == 1)))
            
            if ("BOOKMAKER_HCDELUXE_PJ_S" in skus or
                "BOOKMAKER_HCDELUXE_PJ_D" in skus):
                # Classic Jacketed
                criteria.append(((OrderItem.product_id == 3) &
                                 (OrderItemFeature.cover_type_id == 2)))

            if ("BOOKMAKER_SCPOCKET_IC_S" in skus or
                "BOOKMAKER_SCPOCKET_IC_D" in skus or "STD_PDFPOCKET" in skus):
                # Pocket
                criteria.append(OrderItem.product_id == 1)

            if ("BOOKMAKER_HCBOOK_EC_S" in skus or
                "BOOKMAKER_HCBOOK_EC_D" in skus or
                "BOOKMAKER_HCDELUXE_EC_S" in skus or
                "BOOKMAKER_HCDELUXE_EC_D" in skus):
                # Adhesive
                criteria.append(OrderItemFeature.cover_type_id == 4)

            if "BOOKMAKER_HCBOOK_CJ" in skus or "BOOKMAKER_HCDELUXE_CJ" in skus:
                # Jacket Only
                criteria.append(OrderItem.product_id.in_([8, 9]))

            if "BOOKMAKER_CARD" in skus:
                # Greeting Card
                criteria.append(OrderItem.product_id == 11)

            if "BOOKMAKER_POSTCARD" in skus:
                # Postcard
                criteria.append(OrderItem.product_id == 10)

            if "BOOKMAKER_CALENDAR" in skus:
                # Calendar
                criteria.append(OrderItem.product_id == 12)

            if "GIFT_CERTIFICATE" in skus:
                # Gift Certificate
                criteria.append(OrderItem.product_id == 13)

            if ("APPLE_HCBOOK_EC_D" in skus or
                "APPLE_LGSOFT_IC_D" in skus or
                "APPLE_MDSOFT_IC_D" in skus or
                "APPLE_SMSOFT_IC_D" in skus):
                criteria.append(OrderItem.product_id.between(4, 7))
        
            q = q.filter(or_(*criteria))
                         
        return q

    def _filterByWorkflowState(self, q, params):
        if params.order_state:
            if hasattr(params.order_state, '__iter__'):
                params.order_state = str(params.order_state)[1:-1]
            else:
                params.order_state = "%s" % params.order_state
            q = q.filter(WorkflowItem.state_id.in_(params.order_state))
        return q

    def _getOrderIDs(self, params):
        if params.order_ids.strip():
            params.foids += params.order_ids
        order_ids = []
        if params.foids.strip():
            if params.foids in ("111", "222"):
                order_ids = [params.foids]
            else:
                try:
                    order_ids = map(str, parseOrderIds(params.foids))
                except (ValueError, TypeError):
                    pass
        return order_ids

    def _getProductItemIDs(self, params):
        product_item_ids = []
        if params.book_ids.strip():
            try:
                product_item_ids = map(str, parseOrderIds(params.book_ids))
            except (ValueError, TypeError):
                pass
        return product_item_ids

    def _getRefNums(self, params):
        sep_re = re.compile(r"\W+", re.DOTALL)
        ref_nums = []
        if params.order_numbers.strip():
            ref_nums = [x for x in sep_re.split(params.order_numbers)
                        if x <> ""]
        return ref_nums

    def _filterByIDs(self, q, params):
        order_ids = self._getOrderIDs(params)
        product_item_ids = self._getProductItemIDs(params)
        reference_numbers = self._getRefNums(params)
        
        if order_ids:
            order_criteria = Order.order_id.in_(order_ids)
        else:
            order_criteria = None
            
        if product_item_ids:
            product_item_criteria = ProductItem.product_item_id.in_(
                product_item_ids)
        else:
            product_item_criteria = None

        if reference_numbers:
            reference_number_criteria = Order.reference_number.in_(
                reference_numbers)
        else:
            reference_number_criteria = None

        if (order_criteria or product_item_criteria or
            reference_number_criteria):
            q = q.filter(or_(order_criteria, product_item_criteria,
                             reference_number_criteria))
        return q

    def _filterByStartEnd(self, q, params):
        if params.startfoid and params.endfoid:                
            q = q.filter(between(Order.order_id, params.startfoid,
                                 params.endfoid))
        elif params.startfoid:
            q = q.filter(Order.order_id > params.startfoid)
        elif params.endfoid:
            q = q.filter(Order.order_id < params.endfoid)
        return q
    
    def _filterByFirstName(self, q, params):
        if params.first_name:
            q = q.filter(Customer.first_name.like("%" + params.first_name +
                                                  "%"))
        return q

    def _filterByLastName(self, q, params):
        if params.last_name:
            q = q.filter(Customer.last_name.like("%" + params.last_name + "%"))
        return q

    def _filterByZip(self, q, params):            
        if params.zip:
            zip_codes = [x.strip() for x in params.zip.split(",")
                        if x.strip()]
            for zip_code in zip_codes:
                q = q.filter((ShipAddress.zip_code == zip_code) |
                             (BillAddress.zip_code == zip_code))
        return q

    def _filterByEmail(self, q, params):
        if params.email:
            q = q.filter(Email.email == params.email.strip())
        return q

    def _filterByPromo(self, q, params):
        if params.promo:
            q = q.filter(Promotion.code.like("%" + params.promo.strip() + "%"))
        return q

    def _filterByAssoc(self, q, params):
        if params.assoc:
            q = q.filter(Association.code.like("%" + params.assoc + "%"))
        return q

    def _filterByUserID(self, q, params):
        if params.user_id:
            q = q.filter(Customer.username == params.user_id.strip())
        return q

    def _filterByCoupons(self, q, params):
        if params.coupon_codes.strip():
            coupon_codes = [x for x in re.split("[^\w-]+", params.coupon_codes)
                            if x <> ""]
            q = q.filter(Coupon.code.in_(coupon_codes))
        return q

    def _filterByVersions(self, q, params):
        if params.client:
            if hasattr(params.client, '__iter__'):
                versions = params.client
            else:
                versions = [params.client]             
            for version in versions:
                version = version.replace("bookmaker-mac", "bmm")\
                          .replace("bookmaker", "bm")                
                q = q.filter(SoftwareVersion.code.like("%" + version + "%"))
        return q

    def _filterByGiftCerts(self, q, session, params):
        # XXX This is a problem - how is gift certificate usage
        # distributed amongst the order items in an order where the
        # gift cert was used against the order?
        if params.gc_codes:
            codes = re.split("\W+", params.gc_codes)
            # The GIft Certificate orders match the codes requested
            qry1 = session.query(Invoice2.order_item_id)\
                  .join((OrderItem, OrderItem.order_item_id == 
                                    Invoice2.order_item_id),
                        (GiftCertificate, OrderItem.order_item_id ==
                         GiftCertificate.order_item_id))\
                  .filter(GiftCertificate.gc_code.in_(codes))
            # The orders that had the gift certificate with the matching
            # codes redeemed on them.
            qry2 = session.query(Invoice2.order_item_id)\
                   .join(Payment,
                         (GiftCertificate, (GiftCertificate.order_item_id ==
                                            Payment.gc_order_item_id)))\
                  .filter(GiftCertificate.gc_code.in_(codes))
            qry = qry1.union(qry2)
            results = qry.all()
            ids = []
            for res in results:
                ids += res
            if ids:
                q = q.filter(Order.order_id.in_(ids))
        return q

    def _filterByTransactionNumbers(self, q, params):
        if params.dc_transaction_numbers.strip():
            sep_re = re.compile(r"\W+", re.DOTALL)
            nums = [x for x in sep_re.split(params.dc_transaction_numbers)
                    if x <> '']            
            q = q.filter(PaymentTransaction.transaction_id.in_(nums))
        return q
            
    # -------------------------------------------------------------------------

    def _determineOriginal(self, order_item):
        if order_item.orig_order_item_id:
            orig_order = order_item.orig_order_item.order
        else:
            orig_order = order_item.order
        return orig_order.reference_number
            
    def _determineCurrency(self, obj):
        if obj.currency_id:
            if obj.currency.code == "USD":
                currency = u"$"
            elif obj.currency.code == "GBP":
                currency = u"£"
            elif obj.currency.code == "EUR":
                currency = u"€"
            else:
                currency = ""
        else:
            currency = ""
        return currency

    def _determineCouponCode(self, order):
        coupon_code = promo = ""
        if order.discounts:
            for disc in order.discounts:
                if disc.promotion_id:
                    promo += disc.promotion.code + ", "
                elif disc.coupon_id:
                    coupon_code += disc.coupon.code + ", "
            promo = promo[:-2]
            coupon_code = coupon_code[:-2]
        return coupon_code, promo

    def _determineAssociation(self, order):
        if order.association_id:
            assoc = order.association.name
            if assoc == "n/a":
                assoc = ""
        else:
            assoc = ""
        return assoc

    def _determineChargeDate(self, invoice):
        if invoice:
            for payment in invoice.payments:
                charge_date = Date(payment.payment_date).format("%B %d, %Y")
        else:
            charge_date = None
        return charge_date

    def _determineShippingMethod(self, order, tracking_number):
        if order.shipping_method_id:
            method = order.shipping_method.name
        else:
            method = ""
        method_link = ""
        method_lower = method.lower()
        
        if not (method and tracking_number):
            method_link = ""
        elif "fedex" in method_lower:
            method_link = FEDEX + tracking_number
        elif "usps" in method_lower:
            method_link = USPS
        elif "royal" in method_lower:
            method_link = ROYAL
        elif "ups" in method.lower():
            method_link = UPS
        else:
            method_link = ""
            
        if method:
            method_title = order.shipping_method.description
        else:
            method_title = ""
            
        return method, method_link, method_title

    def _determineProductInfo(self, order_item):
        # XXX For now this stuff will be done only once per Order - in the
        # future we'll show details on multiple items.
        orientation = ""
        cover_thumb = ""
        
        if order_item.feature and order_item.feature.page_siding:
            simplex_duplex = order_item.feature.page_siding.description
        else:
            simplex_duplex = ""
            
        if order_item.product_item_id:
            pi = order_item.product_item
            product_item_id = order_item.product_item_id
            theme = pi.theme.name
            if order_item.order_type == "giftcert":
                # Need to muck with the path to get to the gift cert thumbnail
                cover_thumb = os.path.join(pi.image_basepath.uri, "gift_certs",
                                           "cover_thumb.jpg")                
            else:
                cover_thumb = os.path.join(pi.image_path,
                                           "cover_thumb.jpg")
            if pi.card_orientation:
                orientation = pi.card_orientation.title()
                simplex_duplex = ""
        else:
            product_item_id = theme = None
            
        product = order_item.product.name

        if order_item.product.code.endswith("_bj"):
            cover_color = None
        elif order_item.feature:
            cover_color = order_item.feature.cover_color.name
            code = order_item.feature.cover_type.code
            if code == "bj":
                product += " Jacketed"
            elif code == "pw":
                product += " Picture Window"
            elif code == "pc":
                product += " Softcover"
            elif code == "ad":
                product += " Adhesive Label"
            elif code == "pf":
                product += " Photo Finish"
        else:
            cover_color = None

        if order_item.order_type == "share":
            product = "(Share) " + product
            
        return (orientation, cover_thumb, product, product_item_id,
                simplex_duplex, cover_color, theme)

    def _determineStateInfo(self, session, order, order_item, workflow_item):
        order_state = order.state.name
        show_mfg_state = order_item.state_id < 500

        # XXX assigning everything to order_state and leaving order_item_state
        # empty as it's not yet used.
        order_item_state = ""
        if (workflow_item and
            workflow_item.state_id == State.WAIT):
            delay = self.orders.delay_minutes
            remaining = delay - int(ceil((datetime.now() -
                                          order.purchase_date).seconds / 60))
            order_state = "%s-min Delay (%s min left)" % (delay, remaining)
        elif workflow_item:
            order_state = workflow_item.state.name
        else:
            order_state = order_item.state.name
        return order_state, show_mfg_state, order_item_state

    def _determineCreditCoupon(self, session, order):
        # get coupon/credit history of order
        # XXX How is the refund amount distributed across the
        # various items in an order?
        refunds = []
        creds = session.query(Refund)\
                .filter_by(order_id = order.order_id)\
                .options(eagerload("reason_category"),
                         eagerload("reason_subcategory")).all()
        coups = session.query(Coupon)\
                .filter_by(orig_order_id = order.order_id)\
               .options(eagerload("reason_category"),
                        eagerload("reason_subcategory")).all()
        for refs, kind in((creds, "credit"), (coups, "coupon")):
            for ref in refs:
                date = str(Date(ref.created))
                total = formatDollars(ref.amount, self._determineCurrency(ref))
                refunds.append("%s %s issued a %s %s (%s)" % 
                               (date, ref.user.username, total, kind,
                                ref.comments or
                                ref.reason_subcategory or
                                ref.reason_category))
        return refunds

    def _determineBatchInfo(self, order_item, workflow_item):
        # get Batch info, if applicable.
        batch_state = ""
        show_batch_state = False
        batches = self.batches.getBatchesForOrderItem(order_item.order_item_id,
                                                      active=1)
        if batches:
            batch_id = batches[-1].batch_id
        else:
            batch_id = ""
        if workflow_item and workflow_item.batch_id:
            if (workflow_item.state_id not in (State.INPROGRESS,
                                               State.COMPLETE)):
                show_batch_state = True
                batch_state = workflow_item.state_id
        return batch_id, batch_state, show_batch_state

    def _determineRecipientInfo(self, order_item):
        # get Return Address or Recipient info
        product_group = order_item.product.product_type.name
        return_address = ""
        recipient = recipient_email = gc_code = ""
        gc_amount = gc_amount_redeemed = gc_balance = 0
        
        if product_group == "Card":
            if order_item.return_address:
                for i in range(1, 7):
                    return_address += "%s\n" % getattr(
                        order_item, "return_address%s" % i)
                return_address = return_address.strip()
        elif product_group == "Gift Certificate":
            gift_cert = order_item.gift_certificate
            recipient = gift_cert.recipient_name
            recipient_email = gift_cert.recipient_email.email
            gc_code = gift_cert.gc_code
            gc_amount = gift_cert.amount
            gc_amount_redeemed = gift_cert.redeemed or 0
            gc_balance = gc_amount - gc_amount_redeemed

        return (product_group, return_address, recipient, recipient_email,
                gc_code, gc_amount, gc_amount_redeemed, gc_balance)

    def _findOrdersForGiftCert(self, order_item, product_group):
        """Find the order that have had this gift certificate (if it is one)
        used on them."""
        redeemed_orders = ""
        if product_group == "Gift Certificate":
            redeemed_orders = self.invoices.getRedeemed(order_item)
        return redeemed_orders

    def _findGiftCertsForOrder(self, order_item):
        """Find gift certificates redeemed on this order."""
        gc_data = self.invoices.getGiftCertificateData(order_item)
        gift_certs = []
        for order_item, payment in gc_data:
            if order_item.state_id in (State.CANCEL, State.COMMERCE_CANCEL):
                amount = "0.00"
            else:
                amount = "%0.2f" % Decimal(payment.amount or 0)
            gift_certs.append((order_item.order_id, amount,
                               order_item.gift_certificate.gc_code))
        return gift_certs

    def _determineMfgState(self, workflow_item):
        if workflow_item:
            mfg_state = workflow_item.activity.name or "?"
        else:
            mfg_state = "?"
        return mfg_state

    def _determineVIP(self, order):        
        if order.flags and "vip_order" in order.flags:
            vip = "VIP Order"
        else:
            vip = ""
        return vip

    def _determineDimeURL(self, order_item):
        if order_item.product_item_id:
            name = order_item.product_item.product_file.replace(".pdf", ".dime")
            dime_url = os.path.join(order_item.product_item.download_path.uri,
                                    name)
        else:
            dime_url = ""
        return dime_url

    def _determinePDFURL(self, order_item):
        if order_item.product_item_id:
            pdf_url = os.path.join(order_item.product_item.product_path,
                                   order_item.product_item.product_file)
        else:
            pdf_url = ""
        return pdf_url

    def _determineShipTo(self, order):
        if order.shipping_address_id:
            sa = order.shipping_address        
            ship_to = "%s %s" % (sa.first_name or "", sa.last_name or "")
            ship_to = ship_to.replace("\t", "").replace("  ", " ")\
                      .replace("  ", " ")
            ship_address = "%s %s" % (sa.address1, sa.address2)
            ship_city = sa.city
            ship_state = sa.state
            ship_zip = sa.zip_code
            ship_country = sa.country
            ship_phone = sa.phone
        else:
            ship_to = ship_address = ship_city = ship_state = ship_zip = \
                      ship_country = ship_phone = ""
        return (ship_to, ship_address, ship_city, ship_state, ship_zip,
                ship_country, ship_phone)

    def _determineBillTo(self, order):
        if order.billing_address_id:
            ba = order.billing_address
            bill_to = "%s %s" % (ba.first_name or "", ba.last_name or "")
            bill_to = bill_to.replace("\t", "").replace("  ", " ")\
                      .replace("  ", " ")
            bill_address = "%s %s" % (ba.address1, ba.address2)
            bill_city = ba.city
            bill_state = ba.state
            bill_zip = ba.zip_code
            bill_country = ba.country
            bill_phone = ba.phone
            bill_email = order.email.email
        else:
            c = order.customer
            bill_to = "%s %s" % (c.first_name or "", c.last_name or "")
            bill_address = bill_city = bill_state = bill_zip = bill_phone = ""
            bill_country = c.country_code
            if order.email_id:
                bill_email = order.email.email
            else:
                bill_email = ""
        return (bill_to, bill_address, bill_city, bill_state, bill_zip,
                bill_country, bill_phone, bill_email)

    def _determineMultiFedExShippingInfo(self, session, order):
        # Get multiple fedex shipping info if necessary:
        ship_dates = []
        tracking_numbers = []
        if order.shipping_method_id:
            if "fedex" in order.shipping_method.name.lower():
                # need to coerce order_item_id to str for mysql index usage
                q = session.query(ShippingFedex)\
                    .filter(ShippingFedex.reference_number.in_(
                    [str(oi.order_item_id) for oi in order.items]))\
                    .filter(ShippingFedex.void_date == None)\
                    .order_by(ShippingFedex.ship_date)
                rows = q.all()
                ship_dates = [Date(row.ship_date).format("%B %d, %Y")
                              for row in rows]
                tracking_numbers = [row.tracking_number for row in rows]
            else:
                q1 = session.query(ShippingEndicia.postmark_date,
                                   ShippingEndicia.tracking_number)\
                     .filter(ShippingEndicia.order_item_id.in_(
                     [str(oi.order_item_id) for oi in order.items]))\
                     .filter(ShippingEndicia.postmark_date != None)
                q2 = session.query(ShippingEndiciaHistory.postmark_date,
                                   ShippingEndiciaHistory.tracking_number)\
                     .filter(ShippingEndiciaHistory.order_item_id.in_(
                     [str(oi.order_item_id) for oi in order.items]))\
                     .filter(ShippingEndiciaHistory.postmark_date != None)
                q = q1.union_all(q2)\
                    .order_by(1)
                rows = q.all()
                ship_dates = [Date(row.postmark_date).format("%B %d, %Y")
                              for row in rows]
                tracking_numbers = [row.tracking_number for row in rows]
                
        return ship_dates, tracking_numbers

    def _determineLatestShippingInfo(self, session, order, tracking_numbers,
                                     ship_dates):
        if tracking_numbers:
            tracking_number = tracking_numbers[-1]
        else:
            tracking_number = ""

        if ship_dates:
            ship_date = ship_dates[-1]
            # XXX Not quite making sense here for multiple order items. We are
            #     just getting data on whichever one was last shipped.
            # Check Fedex shipping first
            shipping = session.query(ShippingFedex.net_charge)\
                       .filter(ShippingFedex.reference_number.in_(
                                [str(oi.order_item_id) for oi in order.items]))\
                       .filter(ShippingFedex.void_date == None)\
                       .order_by(desc(ShippingFedex.ship_date)).first()
            if not shipping:
                # ok check endicia
                shipping = session.query(ShippingEndicia.postage_amount)\
                           .filter(ShippingEndicia.order_item_id.in_(
                           [str(oi.order_item_id) for oi in order.items]))\
                           .order_by(desc(ShippingEndicia.postmark_date))\
                           .first()
                if not shipping:
                    # check endicia history
                    shipping = session.query(
                        ShippingEndiciaHistory.postage_amount)\
                        .filter(ShippingEndiciaHistory.order_item_id.in_(
                        [str(oi.order_item_id) for oi in order.items]))\
                        .order_by(desc(ShippingEndiciaHistory.postmark_date))\
                        .first()
                    if not shipping:
                        shipping = Decimal(0)
        else:
            ship_date = ""            
            shipping = Decimal(0)
            
        return ship_date, shipping, tracking_number

    def _determineTransactionNumbers(self, invoice):
        dc_transaction_number = ""
        if invoice:
            for payment in invoice.payments:
                for tran in payment.transactions:
                    if tran.transaction_type.code == "capture":
                        dc_transaction_number += (tran.transaction_id.strip() +
                                                  ", ")
            dc_transaction_number = dc_transaction_number[:-2]
        return dc_transaction_number

    def _determinePaymentProcessors(self, invoice):
        payment_processors = ""
        if invoice:
            for payment in invoice.payments:
                for tran in payment.transactions:
                    processor_name = tran.payment_processor.name
                    if processor_name not in payment_processors:
                        payment_processors += processor_name + ", "
            payment_processors = payment_processors[:-2]
        return payment_processors

    def _gatherComments(self, order):
        # concatenate the comments into a string - str(list)[1:-1] no good here
        comments = ""
        for comment in order.comments:
            comments += comment.txt + "\n"
        return comments
        
    def _assignOrderLevelItems(self, r, session, order_item, workflow_item):
        """Assign values that apply for the overall order as opposed to
        individual order items."""
        r.order_number = r.order.reference_number
        r.original_order_number = self._determineOriginal(order_item)
        if r.order.partner_id:
            r.partner = r.order.partner.name
        else:
            r.partner = ""
        r.addr = ""
        
        r.coupon_code, r.promo = self._determineCouponCode(r.order)
        r.currency = self._determineCurrency(r.order)
        r.assoc = self._determineAssociation(r.order)
        
        r.order_date = Date(r.order.order_date).format("%B %d, %Y")
        r.charge_date = self._determineChargeDate(r.invoice)

        r.date = str(Date(r.order.order_date))
        
        (r.orientation, r.cover_thumb, r.product, r.product_item_id,
         r.simplex_duplex, r.cover_color, r.theme) = \
         self._determineProductInfo(order_item)

        r.order_state, r.show_mfg_state, r.order_item_state = \
                     self._determineStateInfo(session, r.order, order_item,
                                              workflow_item)

        r.refunds = self._determineCreditCoupon(session, r.order)
        
        r.batch_id, r.batch_state, r.show_batch_state = \
                    self._determineBatchInfo(order_item, workflow_item)

        (r.product_group, r.return_address, r.recipient, r.recipient_email,
         r.gc_code, r.gc_amount, r.gc_amount_redeemed, r.gc_balance) = \
         self._determineRecipientInfo(order_item)

        r.redeemed_orders = self._findOrdersForGiftCert(order_item,
                                                        r.product_group)

        r.gift_certs = self._findGiftCertsForOrder(order_item)

        r.mfg_state = self._determineMfgState(workflow_item)
        r.vip = self._determineVIP(r.order)
        r.dime_url = self._determineDimeURL(order_item)
        r.pdf_url = self._determinePDFURL(order_item)

        (r.ship_to, r.ship_address, r.ship_city, r.ship_state, r.ship_zip,
         r.ship_country, r.ship_phone) = self._determineShipTo(r.order)

        (r.bill_to, r.bill_address, r.bill_city, r.bill_state, r.bill_zip,
         r.bill_country, r.bill_phone, r.bill_email) = \
         self._determineBillTo(r.order)

        r.ship_dates, r.tracking_numbers = \
                      self._determineMultiFedExShippingInfo(session, r.order)
        
        r.ship_date, r.shipping, r.tracking_number = \
                     self._determineLatestShippingInfo(session, r.order,
                                                       r.tracking_numbers,
                                                       r.ship_dates)
        if len(r.ship_dates) > 1:
            r.ship_date = None
        else:
            r.ship_dates = []

        if len(r.tracking_numbers) > 1:
            r.tracking_number = None
        else:
            r.tracking_numbers = []

        r.method, r.method_link, r.method_title = \
                  self._determineShippingMethod(r.order, r.tracking_number)

        r.dc_transaction_number = self._determineTransactionNumbers(r.invoice)
        r.payment_processor = self._determinePaymentProcessors(r.invoice)

        if order_item.feature:
            r.leather = order_item.feature.cover_material.name
        else:
            r.leather = ""

        r.comments = self._gatherComments(r.order)
        r.version = r.order.software_version.code\
                    .replace("bmm", "bookmaker-mac")\
                    .replace("bm", "bookmaker")
                             
    def _determineCCPaid(self, order, order_total, gift_certs):
        if order.state == State.CANCEL:
            cc_paid = 0
        else:
            cc_paid = (order_total - sum([Decimal(x[1]) for x in gift_certs]))
        return cc_paid

    def _getFilters(self, q, session, start_date, end_date, params):
        q = self._filterByDate(q, start_date, end_date, params)        
        q = self._filterByShipCountry(q, params)
        q = self._filterByProduct(q, params)        
        q = self._filterByWorkflowState(q, params)
        q = self._filterByIDs(q, params)
        q = self._filterByStartEnd(q, params)
        q = self._filterByFirstName(q, params)
        q = self._filterByLastName(q, params)
        q = self._filterByZip(q, params)
        q = self._filterByEmail(q, params)
        q = self._filterByPromo(q, params)
        q = self._filterByAssoc(q, params)
        q = self._filterByUserID(q, params)
        q = self._filterByCoupons(q, params)
        q = self._filterByVersions(q, params)
        q = self._filterByGiftCerts(q, session, params)
        q = self._filterByTransactionNumbers(q, params)
        return q
    
    def _setupNewRptOrder(self, order_item):
        r = RptOrder()
        r.order = order_item.order                
        if order_item.invoices:
            # XXX Just using first one!
            r.invoice = order_item.invoices[0].invoice
        else:
            r.invoice = None
        r.gross = r.net = r.tax = r.shipping = r.fee = r.cc_paid = \
                  r.order_total = Decimal(0)
        r.qty = r.pages = 0
        return r

    def _accumulateOrderItemFinancials(self, r, order_item):
        r.gross += order_item.gross or 0
        r.net += order_item.net or 0
        r.tax += order_item.tax or 0
        # shipping here means shipping cost and that has yet to be done!
        #shipping += somewhere.shipping or 0
        r.shipping = 0
        r.fee += order_item.shipping or 0
        r.order_item_total = r.gross + r.tax + r.fee        
        r.qty += order_item.qty
        if order_item.product_item:
            r.pages += order_item.product_item.num_pages
        r.order_total += r.net + r.tax + r.fee
        
    @transactional
    def getData(self, session, start_date, end_date, params):
        """Return data on items matching the given date range and params."""
        q = session.query(OrderItem, WorkflowItem)\
            .join(Order, Customer)\
            .outerjoin(WorkflowItem,
                       (ProductItem, (ProductItem.product_item_id ==
                                      OrderItem.product_item_id)),
                       (GiftCertificate, (GiftCertificate.order_item_id ==
                                          OrderItem.order_item_id)),
                       (Association, (Association.association_id ==
                                      Order.association_id)),
                       (OrderItemFeature, (OrderItemFeature.order_item_id ==
                                           OrderItem.order_item_id)),
                       (OrderDiscount, (OrderDiscount.order_id ==
                                        Order.order_id)),
                       (Promotion, (Promotion.promotion_id ==
                                    OrderDiscount.promotion_id)),
                       (Coupon, (Coupon.coupon_id == OrderDiscount.coupon_id)),
                       (SoftwareVersion, (SoftwareVersion.software_version_id==
                                          Order.software_version_id)),
                       (Invoice2, (Invoice2.order_item_id == 
                                   OrderItem.order_item_id)),
                       (Payment, (Payment.invoice_id == Invoice2.invoice_id)),
                       (PaymentTransaction, (PaymentTransaction.payment_id ==
                                             Payment.payment_id)),
                       (BillAddress, (Order.billing_address_id ==
                                      BillAddress.address_id)),
                       (ShipAddress, (Order.shipping_address_id ==
                                      ShipAddress.address_id)),
                       (Email, (Order.email_id == Email.email_id)))
        q = self._getFilters(q, session, start_date, end_date, params)
        q = q.order_by(OrderItem.order_id, OrderItem.order_item_id)
        res = q.all()
        
        order_list = []
        prev_order_id = None
        # Loop through order items and aggregate data up to the order level
        # Use the first order_item as the basis for the book related data
        # for now (thumbnail, cover type etc).  A subsequent project phase
        # will address display multiple order items properly.
        for (order_item, workflow_item) in res:
            if prev_order_id != order_item.order_id:
                if prev_order_id:
                    # Transitioning to another order so finish the calculations
                    # for the current order and append the order data to list
                    r.cc_paid += self._determineCCPaid(
                        r.order, r.order_total, r.gift_certs)
                    r.assignFields(order_list)
                r = self._setupNewRptOrder(order_item)
                prev_order_id = order_item.order_id
                # Figure out all of the order level stuff - this for now 
                # basing a bunch of it off of the first order item so this will
                # need to change once we really support multiple order items.
                self._assignOrderLevelItems(r, session, order_item,
                                            workflow_item)                
            self._accumulateOrderItemFinancials(r, order_item)

        if prev_order_id:
            # Finish up the last order gathered and add it into the order list
            r.cc_paid += self._determineCCPaid(r.order, r.order_total,
                                               r.gift_certs)
            r.assignFields(order_list)

        return order_list
