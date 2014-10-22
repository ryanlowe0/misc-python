#$Id: model.py 7891 2010-04-01 16:37:08Z ryan $

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column as Col, Integer as Int, String, \
                       Date, DateTime, Numeric, ForeignKey as FK, func
from sqlalchemy.orm import relation

# Note: the last_updated, columns don't typically appear in these classes
# because they're mostly for diagnostic purposes and we don't want them to be
# updated directly.

# Classes are listed in alphabetical order.  If a relation refers to a class
# that's defined after it is, then the deferred form is used with class
# passed in as a string.  The same goes for attributes referenced in a primary
# join clause.

class Bcls(object):
    "Provide dict-like access"
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        setattr(self, item, value)
        
Base = declarative_base(cls=Bcls)

class Activity(Base):
    __tablename__ = "activities"
    activity_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    evocation = Col(String)
    entity_type = Col(String)
    active = Col(Int)

class Address(Base):
    __tablename__ = "addresses"
    address_id = Col(Int, primary_key=True)
    customer_id = Col(Int, FK("customers.customer_id"))
    customer = relation('Customer', backref="addresses")
    first_name = Col(String)
    last_name = Col(String)
    address1 = Col(String)
    address2 = Col(String)
    address3 = Col(String)
    city = Col(String)
    state = Col(String)
    zip_code = Col(String)
    country = Col(String)
    phone = Col(String)
    county = Col(String)
    tax_rate = Col(Numeric)
    created = Col(DateTime)
    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def __repr__(self):
        return "<Address('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', " \
               "'%s')>" % (self.address_id, self.customer_id, self.first_name,
                           self.last_name, self.address1, self.city,
                           self.state, self.zip_code, self.country)
        
class Association(Base):
    __tablename__ = "associations"
    association_id = Col(Int, primary_key=True)    
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Audit(Base):
    __tablename__ = "audits"
    # XXX No PK defined on this table! - making one here in SA...
    table_name = Col(String, primary_key=True)
    column_name = Col(String, primary_key=True)
    id = Col(Int)
    code = Col(String)
    old_value = Col(String)
    new_value = Col(String)
    audit_date = Col(DateTime, primary_key=True)

class Batch(Base):
    __tablename__ = "batches"
    batch_id = Col(Int, primary_key=True)
    state_id = Col(Int, FK("states.state_id"))
    state = relation("State")
    press_routing_id = Col(Int, FK("press_routings.press_routing_id"))
    press_routing = relation("PressRouting")
    staple_weight = Col(Int)
    batch_date = Col(DateTime)
    press_id = Col(Int, FK("presses.press_id"))
    press = relation("Press")
    print_reason_id = Col(Int, FK("print_reasons.print_reason_id"))
    print_reason = relation("PrintReason")
    product_id = Col(Int, FK("products.product_id"))
    product = relation("Product")
    components = relation('BatchComponent')
    items = relation('BatchItem')
    def __repr__(self):
        return "<Batch('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')>" % \
               (self.batch_id, self.product_id, self.batch_date, self.state_id,
                self.press_routing_id, self.print_reason_id, self.press_id,
                self.staple_weight)
    @property
    def max_print_run(self):
        return max([c.print_run for c in self.components])

class BatchComponent(Base):
    __tablename__ = "batch_components"
    batch_id = Col(Int, FK("batches.batch_id"), primary_key=True)
    order_item_id = Col(Int, FK("order_items.order_item_id"))
    order_item = relation("OrderItem")
    component_id = Col(Int, FK("components.component_id"), primary_key=True)
    component = relation("Component")
    print_run = Col(Int, primary_key=True)
    num_press_sheets = Col(Int)
    press_filename = Col(String)
    def __repr__(self):
        return "<BatchComponent('%s', '%s', '%s', '%s', '%s', '%s')>" % \
               (self.batch_id, self.component_id, self.print_run,
                self.order_item_id, self.num_press_sheets,
                self.press_filename)
    
class BatchHistory(Base):
    __tablename__ = "batch_history"
    batch_history_id = Col(Int, primary_key=True)
    batch_id = Col(Int, FK("batches.batch_id"))
    batch = relation(Batch)
    activity_id = Col(Int, FK("activities.activity_id"))
    activity = relation(Activity)
    user_id = Col(Int, FK("users.user_id"))
    user = relation("User")
    comments = Col(String)
    history_date = Col(DateTime)    
    entity_type = 'batch'

class BatchItem(Base):
    __tablename__ = "batch_items"
    batch_id = Col(Int, FK("batches.batch_id"), primary_key=True)
    batch = relation("Batch")
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    order_item = relation("OrderItem")
    created = Col(DateTime, primary_key=True)
    qty = Col(Int)
    pages = relation("BatchReworkPage",
                     primaryjoin=("(BatchItem.batch_id == "
                                   "BatchReworkPage.batch_id) & "
                                  "(BatchItem.order_item_id == "
                                   "BatchReworkPage.order_item_id)"),
                     foreign_keys=("BatchReworkPage.batch_id, "
                                   "BatchReworkPage.order_item_id"))
    active = Col(Int)
    removed_date = Col(DateTime)
    def __repr__(self):
        return "<BatchItem('%s', '%s', '%s', '%s', '%s', '%s')>" % \
               (self.batch_id, self.order_item_id, self.created, self.qty,
                self.active, self.removed_date)
    
class BatchReworkPage(Base):
    __tablename__ = "batch_rework_pages"
    batch_id = Col(Int, FK("batches.batch_id"), primary_key=True)
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    page = Col(Int)
    qty = Col(Int)

class Calendar(Base):
    __tablename__ = "calendar"
    calendar_date = Col(Date, primary_key=True)
    is_business_day = Col(Int)

class Component(Base):
    __tablename__ = "components"
    CONTENT = 1
    COVER = 2
    JACKET = 3
    ENVELOPE = 4
    PHOTO_FINISH = 5
    component_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    def __repr__(self):
        return "<Component('%s', '%s', '%s', '%s', '%s')>" % \
               (self.component_id, self.code, self.name, self.description,
                self.active)
    
class Country(Base):
    __tablename__ = "countries"
    country_code = Col(String, primary_key=True)
    name = Col(String)

class Coupon(Base):
    __tablename__ = "coupons"
    coupon_id = Col(Int, primary_key=True)
    code = Col(String)
    currency_id = Col(Int, FK("currencies.currency_id"))
    currency = relation("Currency")
    coupon_type = Col(String)
    user_id = Col(Int, FK("users.user_id"))
    user = relation("User", primaryjoin="Coupon.user_id == User.user_id")
    refund_reason_category_id = Col(
        Int, FK("refund_reason_categories.refund_reason_category_id"))
    reason_category = relation("RefundReasonCategory")
    refund_reason_subcategory_id = Col(
        Int, FK("refund_reason_subcategories.refund_reason_subcategory_id"))
    reason_subcategory = relation("RefundReasonSubCategory")
    amount = Col(Numeric)
    shipping_method_id = Col(Int)
    orig_order_id = Col(Int, FK("orders.order_id"))
    orig_order = relation("Order")
    comments = Col(String)
    created = Col(DateTime)
    verified_by = Col(Int, FK("users.user_id"))
    verified_date = Col(DateTime)
    def __repr__(self):
        return "<Coupon('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', " \
               "'%s', '%s', '%s', '%s', '%s', '%s')>" % \
               (self.coupon_id, self.code, self.currency_id,
                self.coupon_type, self.user_id, self.refund_reason_category_id,
                self.refund_reason_subcategory_id, self.amount,
                self.shipping_method_id, self.orig_order_id, self.comments,
                self.created, self.verified_by, self.verified_date)

class Courier(Base):
    __tablename__ = "couriers"
    courier_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class CoverColor(Base):
    __tablename__ = "cover_colors"
    cover_color_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
        
class CoverStyle(Base):
    __tablename__ = "cover_styles"
    cover_style_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class CoverMaterial(Base):
    __tablename__ = "cover_materials"
    cover_material_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)    

class CoverType(Base):
    __tablename__ = "cover_types"
    cover_type_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    
class Currency(Base):
    __tablename__ = "currencies"
    USD, GBP, EUR = (1, 2, 3)
    currency_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    symbol = Col(String)
    
class Customer(Base):
    __tablename__ = "customers"
    comments = relation("CustomerComment")
    customer_id = Col(Int, primary_key=True)
    reference_number = Col(String)
    username = Col(String, unique=True)
    first_name = Col(String)
    last_name = Col(String)
    language_code = Col(String, FK("languages.language_code"))    
    country_code = Col(String, FK("countries.country_code"))
    country = relation('Country')
    start_date = Col(DateTime)
    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def __repr__(self):
        return "<Customer('%s', '%s', '%s', '%s')>" % (
            self.customer_id, self.username, self.first_name, self.last_name)
    
class CustomerComment(Base):
    __tablename__ = "customer_comments"
    customer_id = Col(Int, FK("customers.customer_id"), primary_key=True)
    comment_date = Col(DateTime, primary_key=True)
    user_id = Col(Int, FK("users.user_id"))    
    txt = Col(String)

class DataCenter(Base):
    __tablename__ = "data_centers"
    data_center_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Email(Base):
    __tablename__ = "emails"
    email_id = Col(Int, primary_key=True)
    customer_id = Col(Int, FK("customers.customer_id"))
    customer = relation(Customer, backref="emails")
    email = Col(String)
    created = Col(DateTime)
    email_usages = relation("EmailUsage")
    def __repr__(self):
        return "<Email('%s', '%s')>" % (self.email_id, self.email)

class EmailActivity(Base):
    __tablename__ = "email_activities"
    entity_id = Col(Int, primary_key=True)
    entity_type_id = Col(Int, primary_key=True)
    email_tracking_type_id = Col(Int, primary_key=True)
    email_link_id = Col(Int, primary_key=True)
    activity_date = Col(DateTime)
    link_num = Col(Int)
   
class EmailLink(Base):
    __tablename__ = "email_links"
    email_link_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    url = Col(String)
    description = Col(String)        
    active = Col(Int)

class EmailTrackingType(Base):
    __tablename__ = "email_tracking_types"
    email_tracking_type_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    active = Col(Int)
    description = Col(String)    

class EmailTracking(Base):
    __tablename__ = "email_tracking"
    entity_id = Col(Int, primary_key=True)
    entity_type_id = Col(Int, primary_key=True)
    email_tracking_type_id = Col(Int, primary_key=True)
    sent = Col(DateTime)
    opened_date = Col(DateTime)
    opened_cnt = Col(Int)
    bounced = Col(DateTime)

class EmailType(Base):
    __tablename__ = "email_types"
    ORDER, SHARER, SHAREE, GIFTCERT, GIFTCERT_TO = range(1, 6)
    email_type_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    def __repr__(self):
        return "<EmailType('%s', '%s', '%s', '%s', '%s')>" \
               % (self.email_type_id, self.code, self.name, self.description,
                  self.active)
    
class EmailUsage(Base):
    __tablename__ = "email_usages"
    email_id = Col(Int, FK("emails.email_id"), primary_key=True)
    email_type_id = Col(Int, FK("email_types.email_type_id"), primary_key=True)
    def __repr__(self):
        return "<EmailUsage('%s', '%s')>" % (self.email_id, self.email_type_id)
    
class EntityType(Base):
    __tablename__ = "entity_types"
    entity_type_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)

class ErrorReport(Base):
    __tablename__ = "error_report"
    order_item_id = Col(Int, primary_key=True)
    error_date = Col(DateTime)
    error_reason = Col(String)

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    rate_date = Col(Date, primary_key=True)
    currency_id = Col(Int, FK("currencies.currency_id"), primary_key=True)
    rate = Col(Numeric)

class ExternalShare(Base):
    __tablename__ = "external_shares"
    share_id = Col(Int, primary_key=True)
    product_item_id = Col(Int, FK("product_items.product_item_id"))
    product_item = relation("ProductItem")
    website_id = Col(Int)
    share_date = Col(DateTime)

class ExternalView(Base):
    __tablename__ = "external_views"
    view_id = Col(Int, primary_key=True)
    product_item_id = Col(Int, FK("product_items.product_item_id"))
    product_item = relation("ProductItem")
    website_id = Col(Int)
    view_date = Col(DateTime)

class Facility(Base):
    __tablename__ = "facilities"
    facility_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    
class GCReport(Base):
    __tablename__ = "gc_report"
    activity_date = Col(DateTime)
    activity_type = Col(String, primary_key=True)
    purchaser = Col(String)
    recipient = Col(String)
    orig_amount = Col(Numeric)
    running_balance = Col(Numeric)
    activity_amount = Col(Numeric)
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    gc_purchase_date = Col(DateTime)
    gc_code = Col(String)
    transaction_id = Col(String)

class GiftCertificate(Base):
    __tablename__ = "gift_certificates"
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    order_item = relation("OrderItem")
    gc_code = Col(String)
    sender_name = Col(String)
    recipient_name = Col(String)
    amount = Col(Numeric)
    recipient_email_id = Col(Int, FK("emails.email_id"))
    recipient_email = relation(Email)
    redeemed = Col(Numeric)
    def __repr__(self):
        return "<GiftCertificate('%s', '%s', '%s', '%s', '%s', '%s', '%s')>" \
               % (self.order_item_id, self.gc_code, self.sender_name,
                  self.recipient_name, self.amount, self.recipient_email_id,
                  self.redeemed)
    
class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id = Col(Int, primary_key=True)
    invoice_date = Col(DateTime)
    state_id = Col(Int, FK("states.state_id"))
    state = relation("State")
    amount = Col(Numeric)
    tax = Col(Numeric)
    shipping = Col(Numeric)
    ship_date = Col(DateTime)
    shipping_cost = Col(Numeric)
    tracking_number = Col(String)
    payments = relation("Payment", primaryjoin=(
        "Invoice.invoice_id == Payment.invoice_id"))

    def __repr__(self):
        return "<Invoice('%s', '%s', '%s', '%s', '%s', '%s')>" \
               % (self.invoice_id, self.invoice_date, self.state_id,
                  self.amount, self.tax, self.shipping)

class Invoice2(Base):   # view for reports (assumes one per order_item)
    __tablename__ = "invoices2"
    invoice_id = Col(Int, primary_key=True)
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    amount = Col(Numeric)
    tax = Col(Numeric)
    shipping = Col(Numeric)
    ship_date = Col(DateTime)
    shipping_cost = Col(Numeric)
    tracking_number = Col(String)

class InvoiceOrderItem(Base):
    __tablename__ = "invoice_order_items"
    invoice_id = Col(Int, FK("invoices.invoice_id"), primary_key=True)
    invoice = relation(Invoice)
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    order_item = relation("OrderItem")

class Language(Base):
    __tablename__ = "languages"
    language_code = Col(String, primary_key=True)
    name = Col(String)

class Login(Base):
    __tablename__ = "logins"
    user_id = Col(Int, FK("users.user_id"), primary_key=True)
    login_cnt = Col(Int)
    last_updated = Col(DateTime)

class Location(Base):   # view
    __tablename__ = "locations"
    activity_code = Col(String)
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    location = Col(String)
    
class Order(Base):
    __tablename__ = "orders"
    order_id = Col(Int, primary_key=True)
    reference_id = Col(Int)
    reference_number = Col(String)
    email_id = Col(Int, FK("emails.email_id"))
    email = relation(Email)
    comments = relation("OrderComment")
    customer_id = Col(Int, FK("customers.customer_id"))
    customer = relation(Customer, backref="orders")
    billing_address_id = Col(Int, FK("addresses.address_id"))
    billing_address = relation(Address, primaryjoin=billing_address_id ==
                                                    Address.address_id)
    shipping_address_id = Col(Int, FK("addresses.address_id"))
    shipping_address = relation(Address, primaryjoin=shipping_address_id ==
                                                     Address.address_id)
    software_version_id = Col(Int, FK("software_versions.software_version_id"))
    software_version = relation("SoftwareVersion")
    state_id = Col(Int, FK("states.state_id"))
    state = relation("State")
    partner_id = Col(Int, FK("partners.partner_id"))
    partner = relation("Partner")
    association_id = Col(Int, FK("associations.association_id"))
    association = relation(Association)
    currency_id = Col(Int, FK("currencies.currency_id"))
    currency = relation(Currency)
    facility_id = Col(Int, FK("facilities.facility_id"))
    facility = relation(Facility)
    shipping_method_id = Col(Int, FK("shipping_methods.shipping_method_id"))
    shipping_method = relation("ShippingMethod")
    order_date = Col(DateTime)
    purchase_date = Col(DateTime)
    cancel_date = Col(DateTime)
    flags = Col(String)
    items = relation("OrderItem")
    discounts = relation("OrderDiscount")

    def __repr__(self):
        return "<Order('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', "\
               "'%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')>" % (
            self.order_id, self.reference_id, self.reference_number,
            self.email_id, self.customer_id, self.billing_address_id,
            self.shipping_address_id, self.software_version_id, self.state_id,
            self.partner_id, self.association_id, self.currency_id,
            self.facility_id, self.shipping_method_id, self.order_date,
            self.purchase_date, self.flags)

class OrderComment(Base):
    __tablename__ = "order_comments"
    order_id = Col(Int, FK("orders.order_id"), primary_key=True)
    comment_date = Col(DateTime, primary_key=True)
    user_id = Col(Int, FK("users.user_id"))    
    txt = Col(String)

class OrderEntryData(Base):
    __tablename__ = "order_entry"
    partnerReference = Col(String, primary_key=True)
    puchase_type = Col(Int)
    purchaseDate = Col(DateTime)
    partnerSession = Col(String)
    clientSignature = Col(String)
    distribId = Col(String)
    currency = Col(String)
    partnerId = Col(String)
    print_return_address = Col(String)
    quantity = Col(Int)
    gross = Col(Numeric)
    price = Col(Numeric)
    tax = Col(Numeric)
    shippingPrice = Col(Numeric)
    sku = Col(String)
    coverColor = Col(String)
    leather = Col(String)
    pageCount = Col(Int)
    calendar_start_date = Col(Date)
    orientation = Col(String)
    contentUrl = Col(String)
    theme = Col(String)
    coverLayout = Col(String)
    promotionId = Col(String)
    couponCode = Col(String)
    customerGuid = Col(String)
    userId = Col(String)
    userFirstName = Col(String)
    userLastName = Col(String)
    language = Col(String)
    country = Col(String)
    billingFirstName = Col(String)
    billingLastName = Col(String)
    billingAddress1 = Col(String)
    billingAddress2 = Col(String)
    billingAddress3 = Col(String)
    billingCity = Col(String)
    billingState = Col(String)
    billingZip = Col(String)
    billingCountry = Col(String)
    billingPhone = Col(String)
    shippingFirstName = Col(String)
    shippingLastName = Col(String)
    shippingAddress1 = Col(String)
    shippingAddress2 = Col(String)
    shippingAddress3 = Col(String)
    shippingCity = Col(String)
    shippingState = Col(String)
    shippingCountry = Col(String)
    shippingZip = Col(String)
    shippingPhone = Col(String)
    taxRate = Col(Numeric)
    taxCounty = Col(String)
    return_address1 = Col(String)
    return_address2 = Col(String)
    return_address3 = Col(String)
    return_address4 = Col(String)
    return_address5 = Col(String)
    return_address6 = Col(String)
    last_updated = Col(DateTime)

class OrderDiscount(Base):
    __tablename__ = "order_discounts"
    order_discount_id = Col(Int, primary_key=True)
    order_id = Col(Int, FK("orders.order_id"))
    order = relation("Order")
    promotion_id = Col(Int, FK("promotions.promotion_id"))
    promotion = relation("Promotion")
    coupon_id = Col(Int, FK("coupons.coupon_id"))
    coupon = relation("Coupon")
    discount_amount = Col(Numeric)
    discount_type = Col(String)
    
class OrderItem(Base):
    __tablename__ = "order_items"
    comments = relation("OrderItemComment")
    order_item_id = Col(Int, primary_key=True)
    order_id = Col(Int, FK("orders.order_id"))
    order = relation(Order)
    orig_order_item_id = Col(Int, FK("order_items.order_item_id"))
    orig_order_item = relation("OrderItem",
                               primaryjoin=order_item_id == orig_order_item_id,
                               remote_side=order_item_id)
    order_type = Col(String)
    state_id = Col(Int, FK("states.state_id"))
    state = relation("State")
    qty = Col(Int)
    gross = Col(Numeric)
    net = Col(Numeric)
    tax = Col(Numeric)
    shipping = Col(Numeric)
    flags = Col(String)
    message = relation("OrderItemMessage")
    feature = relation("OrderItemFeature", uselist=False)
    product_id = Col(Int, FK("products.product_id"))
    product = relation("Product")
    product_item_id = Col(Int, FK("product_items.product_item_id"))    
    product_item = relation("ProductItem", uselist=False)
    sku_id = Col(Int, FK("skus.sku_id"))
    sku = relation("Sku")
    return_address = relation("ReturnAddress", uselist=False)
    gift_certificate = relation(GiftCertificate,
                                primaryjoin=order_item_id ==
                                            GiftCertificate.order_item_id,
                                uselist=False)
    batch_items = relation(BatchItem)
    sharees = relation("Sharee")
    invoices = relation(InvoiceOrderItem)
    
    def __repr__(self):
        return "<OrderItem('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', " \
               "'%s', '%s', '%s', '%s', '%s')>" % (
            self.order_item_id, self.order_id,
            self.orig_order_item_id, self.product_id,
            self.product_item_id, self.order_type, self.state_id,
            self.qty, self.gross, self.net, self.tax, self.shipping,
            self.flags)
    
class OrderItemComment(Base):
    __tablename__ = "order_item_comments"
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    comment_date = Col(DateTime, primary_key=True)
    user_id = Col(Int, FK("users.user_id"))    
    txt = Col(String)

class OrderItemFeature(Base):
    __tablename__ = "order_item_features"    
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    cover_type_id = Col(Int, FK("cover_types.cover_type_id"))
    cover_type = relation(CoverType)
    cover_material_id = Col(Int, FK("cover_materials.cover_material_id"))
    cover_material = relation(CoverMaterial)
    cover_color_id = Col(Int, FK("cover_colors.cover_color_id"))
    cover_color = relation(CoverColor)
    page_siding_id = Col(Int, FK("page_sidings.page_siding_id"))
    page_siding = relation("PageSiding")
    press_routing = relation("PressRouting",
                             primaryjoin=(order_item_id ==
                                          OrderItem.order_item_id),
                             secondaryjoin=(
                                    "(OrderItem.order_item_id == "
                                    " OrderItemFeature.order_item_id) & "
                                    "(OrderItem.product_id =="
                                    " PressRouting.product_id) & "
                                    "(OrderItemFeature.cover_type_id =="
                                    " PressRouting.cover_type_id) &"
                                    "(PressRouting.active == 1)"),
                             secondary="press_routings",
                             foreign_keys=("OrderItem.order_item_id, "
                                           "OrderItem.product_id, "
                                           "OrderItemFeature.cover_type_id"),
                             uselist=False)

class OrderItemHistory(Base):
    __tablename__ = "order_item_history"
    order_item_history_id = Col(Int, primary_key=True)
    order_item_id = Col(Int, FK("order_items.order_item_id"))
    order_item = relation("OrderItem")
    activity_id = Col(Int, FK("activities.activity_id"))
    activity = relation(Activity)
    user_id = Col(Int, FK("users.user_id"))
    user = relation("User")
    comments = Col(String)
    history_date = Col(DateTime)    
    entity_type = 'order_item'

class OrderItemMessage(Base):
    __tablename__ = "order_item_messages"
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    message = Col(String)
    
class PageSiding(Base):
    __tablename__ = "page_sidings"
    page_siding_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Partner(Base):
    __tablename__ = "partners"
    partner_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Col(Int, primary_key=True)
    invoice_id = Col(Int, FK("invoices.invoice_id"))
    invoice = relation(Invoice)
    payment_type_id = Col(Int, FK("payment_types.payment_type_id"))
    payment_type = relation("PaymentType")
    gc_order_item_id = Col(Int, FK("gift_certificates.order_item_id"))
    amount = Col(Numeric)
    payment_date = Col(DateTime)
    transactions = relation("PaymentTransaction")
    def __repr__(self):
        return "<Payments('%s', '%s', '%s', '%s', '%s', '%s')>" \
               % (self.payment_id, self.invoice_id, self.payment_type_id,
                  self.gc_order_item_id, self.amount, self.payment_date)

class PaymentProcessor(Base):
    __tablename__ = "payment_processors"
    payment_processor_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class PaymentProcessorTransactionType(Base):
    __tablename__ = "payment_processor_transaction_types"
    payment_processor_transaction_type_id = Col(Int, primary_key=True)
    payment_processor_id = Col(Int, FK("payment_processors"))
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    payment_transaction_type_id = Col(Int, FK("payment_transaction_type"))
    
class PaymentReturnCode(Base):
    __tablename__ = "payment_return_codes"
    AUTHORIZENET_APPROVED = 122 # '1'
    WORLDPAY_APPROVED = 114   # 'A'    
    payment_return_code_id = Col(Int, primary_key=True)
    transaction_return_code = Col(String)
    payment_processor_id = Col(Int, FK("payment_processors"))
    payment_processor = relation(PaymentProcessor)
    description = Col(String)
    active = Col(Int)    

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    payment_transaction_id = Col(Int, primary_key=True)
    payment_id = Col(Int, FK("payments.payment_id"))
    payment = relation(Payment)
    payment_processor_id = Col(Int, FK("payment_processors"))
    payment_processor = relation(PaymentProcessor)
    payment_transaction_type_id = Col(Int, FK("payment_transaction_types"))
    transaction_type = relation("PaymentTransactionType")
    payment_return_code_id = Col(Int, FK("payment_return_codes"))
    return_code = relation(PaymentReturnCode)
    transaction_id = Col(String)
    transaction_date = Col(DateTime)
    amount = Col(Numeric)

class PaymentTransactionType(Base):
    __tablename__ = "payment_transaction_types"
    AUTHORIZE, SALE, CAPTURE, CATPURE_ONLY, VOID, CREDIT = range(1, 7)
    payment_transaction_type_id = Col(Int, primary_key=True)
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)    

class PaymentType(Base):
    __tablename__ = "payment_types"
    CREDIT_CARD, CHECK, GIFT_CERTIFICATE = 1, 2, 3
    payment_type_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)    

class Permission(Base):
    __tablename__ = "permissions"
    permission_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)    
    
class Press(Base):
    __tablename__ = "presses"
    press_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)    

class PressRouting(Base):
    __tablename__ = "press_routings"
    press_routing_id = Col(Int, primary_key=True)
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    product_id = Col(Int, FK("products.product_id"))
    product = relation("Product")
    cover_type_id = Col(Int, FK("cover_types.cover_type_id"))
    cover_type = relation(CoverType)
    last_updated = Col(DateTime)
    page_siding_id = Col(Int, FK("page_sidings.page_siding_id"))
    page_siding = relation(PageSiding)
    presses = relation("PressRoutingPress", primaryjoin=
                       "(PressRouting.press_routing_id =="
                       " PressRoutingPress.press_routing_id) &"
                       "(PressRoutingPress.work_type == 'new')")
    rework_presses = relation("PressRoutingPress", primaryjoin=
                              "(PressRouting.press_routing_id =="
                              " PressRoutingPress.press_routing_id) &"
                              "(PressRoutingPress.work_type == 'rework')")
    user_id = Col(Int, FK("users.user_id"))
    user = relation("User")

class PressRoutingPress(Base):
    __tablename__ = "press_routing_presses"
    press_routing_id = Col(Int, FK("press_routings.press_routing_id"),
                           primary_key=True)
    press_id = Col(Int, FK("presses.press_id"), primary_key=True)
    press = relation(Press)
    work_type = Col(String, primary_key=True)

class PrintReason(Base):
    __tablename__ = "print_reasons"
    NEW, RESEND, REWORK, AGING, OVERRIDE = range(10, 60, 10)
    print_reason_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    priority = Col(Int)
    active = Col(Int)        
    
class Product(Base):
    __tablename__ = "products"
    POSTCARD = 10
    CARD = 11
    CALENDAR = 12
    GIFTCERT = 13
    product_id = Col(Int, primary_key=True)
    pages_per_side = Col(Int)
    sheets_per_stack = Col(Int)
    max_wait = Col(Int)
    max_wait_rework = Col(Int)
    harmonized_code = Col(String)
    product_type_id = Col(Int, FK("product_types.product_type_id"))
    product_type = relation("ProductType")
    product_components = relation("ProductComponent", 
                                  primaryjoin="ProductComponent.product_id == "
                                              "Product.product_id")
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class ProductComponent(Base):
    __tablename__ = "product_components"
    product_id = Col(Int, FK("products.product_id"), primary_key=True)
    product = relation(Product)
    component_id = Col(Int, FK("components.component_id"), primary_key=True)
    component = relation(Component)
    description = Col(String)
    single_pdf = Col(Int)
    needs_queueing = Col(Int)
    active = Col(Int)
    def __repr__(self):
        return "<Component('%s', '%s', '%s', '%s', '%s', '%s')>" % \
               (self.product_id, self.component_id, self.description,
                self.single_pdf, self.needs_queueing, self.active)

class ProductCoverType(Base):
    __tablename__ = "product_cover_types"
    product_cover_type_id = Col(Int, primary_key=True)
    product_id = Col(Int)
    cover_type_id = Col(Int)
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    
class ProductItem(Base):
    __tablename__ = "product_items"
    product_item_id = Col(Int, primary_key=True)
    orig_customer_id = Col(Int, FK("customers.customer_id"))
    orig_customer = relation("Customer")
    num_pages = Col(Int)
    theme_id = Col(Int, FK("themes.theme_id"))
    theme = relation("Theme")
    cover_style_id = Col(Int, FK("cover_styles.cover_style_id"))
    cover_style = relation(CoverStyle)
    calendar_start_date = Col(DateTime)
    card_orientation = Col(String)
    state_id = Col(Int, FK("states.state_id"))
    state = relation("State")
    product_file = Col(String)
    download_path_id = Col(Int, FK("uri_resources.uri_resource_id"))
    download_path = relation("UriResource",
                             primaryjoin="ProductItem.download_path_id == "
                                         "UriResource.uri_resource_id")
    product_basepath_id = Col(Int, FK("uri_resources.uri_resource_id"))
    product_basepath = relation("UriResource", primaryjoin=
                                "ProductItem.product_basepath_id == "
                                "UriResource.uri_resource_id")
    image_basepath_id = Col(Int, FK("uri_resources.uri_resource_id"))
    image_basepath = relation("UriResource",
                              primaryjoin="ProductItem.image_basepath_id == "
                                          "UriResource.uri_resource_id")
    order_items = relation('OrderItem')
    flags = Col(String)
    created = Col(DateTime)
    @property
    def product_path(self):
        from plant.smartdate import Date
        return '/'.join([self.product_basepath.uri.replace('file:/', '', 1),
                         str(Date(self.created)),
                         str(self.product_item_id)])
    @property
    def download_filepath(self):
        return '/'.join([self.download_path.uri, self.product_file])
    @property
    def product_filepath(self):
        return '/'.join([self.product_path, self.product_file])
    @property
    def image_path(self):
        return '/'.join([self.image_basepath.uri,
                         str(self.product_item_id)])
    def __repr__(self):
        return "<ProductItem('%s', '%s', '%s', '%s', '%s', '%s')>" % (
            self.product_item_id, self.num_pages, self.theme_id,
            self.cover_style_id, self.product_file, self.flags)
    def flatdata(self):
        return {'product_item_id': self.product_item_id,
                'orig_customer': self.orig_customer.full_name,
                'num_pages': self.num_pages,
                'theme': self.theme.code,
                'cover_style': self.cover_style.code,
                'calendar_start_date': self.calendar_start_date,
                'card_orientation': self.card_orientation,
                'state': self.state.code,
                'product_file': self.product_file,
                'product_path': self.product_path,
                'product_filepath': self.product_filepath,
                'download_path': self.download_path.uri,
                'download_filepath': self.download_filepath,
                'image_path': self.image_path,
                'flags': self.flags,
                'order_item(s)': ', '.join(map(str,
                                               (x['order_item_id'] \
                                                for x in self.order_items))),
                'created': self.created}
    
class ProductItemHistory(Base):
    __tablename__ = "product_item_history"
    product_item_history_id = Col(Int, primary_key=True)
    product_item_id = Col(Int, FK("product_items.product_item_id"))
    product_item = relation("ProductItem")
    activity_id = Col(Int, FK("activities.activity_id"))
    activity = relation(Activity)
    user_id = Col(Int, FK("users.user_id"))
    user = relation("User")
    comments = Col(String)
    history_date = Col(DateTime)
    entity_type = 'product_item'

class ProductType(Base):
    __tablename__ = "product_types"
    product_type_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Promotion(Base):
    __tablename__ = "promotions"
    promotion_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)

class UriResource(Base):
    __tablename__ = "uri_resources"
    uri_resource_id = Col(Int, primary_key=True)
    unit = Col(Int)
    data_center_id = Col(Int, FK("data_centers.data_center_id"))
    data_center = relation(DataCenter)
    uri = Col(String)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    def __repr__(self):
        return "<UriResource('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')>"\
               % (self.uri_resource_id, self.code, self.unit, self.name,
                  self.description, self.data_center_id, self.uri, self.active)
        
class Refund(Base):
    __tablename__ = "refunds"
    refund_id = Col(Int, primary_key=True)
    order_id = Col(Int, FK("orders.order_id"))
    user_id = Col(Int, FK("users.user_id"))
    user = relation("User", primaryjoin="Refund.user_id == User.user_id")
    refund_reason_category_id = Col(
        Int, FK("refund_reason_categories.refund_reason_category_id"))
    reason_category = relation("RefundReasonCategory")
    refund_reason_subcategory_id = Col(
        Int, FK("refund_reason_subcategories.refund_reason_subcategory_id"))
    reason_subcategory = relation("RefundReasonSubCategory")
    comments = Col(String)
    gross = Col(Numeric)
    tax = Col(Numeric)
    shipping = Col(Numeric)
    state_id = Col(Numeric)
    new_transaction_id = Col(String)
    transaction_date = Col(DateTime)
    created = Col(DateTime)
    verified_by = Col(Int, FK("users.user_id"))
    verified_date = Col(DateTime)

class RefundReasonCategory(Base):
    __tablename__ = "refund_reason_categories"
    COUPON = 1
    refund_reason_category_id = Col(Int, primary_key=True)
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
               
class RefundReasonSubCategory(Base):
    __tablename__ = "refund_reason_subcategories"
    refund_reason_subcategory_id = Col(Int, primary_key=True)
    refund_reason_category_id = Col(
        Int, FK("refund_reason_categories.refund_reason_category_id"))
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    
class ReturnAddress(Base):
    __tablename__ = "return_addresses"
    return_address_id = Col(Int, primary_key=True)
    order_item_id = Col(Int, FK("order_items.order_item_id"))
    address1 = Col(String)
    address2 = Col(String)
    address3 = Col(String)
    address4 = Col(String)
    address5 = Col(String)
    address6 = Col(String)
                        
class Rework(Base):
    __tablename__ = "reworks"
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    order_item = relation(OrderItem)
    print_reason_id = Col(Int, FK("print_reasons.print_reason_id"))
    print_reason = relation(PrintReason)
    rework_reason_id = Col(Int, FK("rework_reasons.rework_reason_id"))
    rework_reason = relation("ReworkReason")
    rework_date = Col(DateTime)
    qty = Col(Int)

class ReworkReason(Base):
    __tablename__ = "rework_reasons"
    rework_reason_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Role(Base):
    __tablename__ = "roles"
    role_id = Col(Int, primary_key=True)
    code = Col(String)
    name = Col(String, unique=True)
    description = Col(String)
    active = Col(Int)
    
class Sharee(Base):
    __tablename__ = "sharees"
    order_item_id = Col(Int, FK("order_items.order_item_id"), primary_key=True)
    order_item = relation(OrderItem)
    sharee_id = Col(Int, primary_key=True)
    email_id = Col(Int, FK("emails.email_id"))
    email = relation(Email)

class ShippingEndicia(Base):    
    __tablename__ = "shipping_endicia"
    ENDICIA_METHODS = ('PM', 'USPS_FLAT_RATE', 'USPS_PARCEL', 'fedex_int_mail',
                       'PMI')
    order_item_id = Col(Int, primary_key=True)
    orig_mail_class = Col(String)
    name = Col(String)
    last_name = Col(String)
    company = Col(String)
    address1 = Col(String)
    address2 = Col(String)
    address3 = Col(String)
    city = Col(String)
    state = Col(String)
    zip_code = Col(String)
    country = Col(String)
    email = Col(String)
    phone = Col(String)
    email_class = Col(String) 
    postage_amount = Col(Numeric)
    tracking_number = Col(String)
    postmark_date = Col(DateTime) 
    transaction_datetime = Col(DateTime)
    transaction_id = Col(Int)
    group_code = Col(String)
    insured_value = Col(Numeric)
    insurance_fee = Col(Numeric)
    status = Col(String)
    weight = Col(Numeric)

class ShippingEndiciaHistory(Base):
    __tablename__ = "shipping_endicia_history"
    order_item_id = Col(Int, primary_key=True)
    orig_mail_class = Col(String)
    name = Col(String)
    last_name = Col(String)
    company = Col(String)
    address1 = Col(String)
    address2 = Col(String)
    address3 = Col(String)
    city = Col(String)
    state = Col(String)
    zip_code = Col(String)
    country = Col(String)
    email = Col(String)
    phone = Col(String)
    email_class = Col(String) 
    postage_amount = Col(Numeric)
    tracking_number = Col(String)
    postmark_date = Col(DateTime) 
    transaction_datetime = Col(DateTime)
    transaction_id = Col(Int)
    group_code = Col(String)
    insured_value = Col(Numeric)
    insurance_fee = Col(Numeric)
    status = Col(String)
    weight = Col(Numeric)
    last_updated = Col(DateTime, primary_key=True)
    
class ShippingFedex(Base):
    __tablename__ = "shipping_fedex"
    shipping_fedex_id = Col(Int, primary_key=True)
    ship_date = Col(DateTime)
    user_id = Col(String)
    reference_number = Col(String)
    shipment_no = Col(Int)
    tracking_number = Col(String)
    billed_weight = Col(Numeric)
    actual_weight = Col(Numeric)
    net_charge = Col(Numeric)
    service_type = Col(String)
    zone = Col(String)
    void_date = Col(DateTime)
    saturday_delivery = Col(String)
    picked_up = Col(DateTime)
    delivered = Col(DateTime)

class ShippingMethod(Base):
    __tablename__ = "shipping_methods"
    shipping_method_id = Col(Int, primary_key=True)
    courier_id = Col(Int)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class SoftwareClient(Base):
    __tablename__ = "software_clients"
    software_client_id = Col(Int, primary_key=True)
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class SoftwareVersion(Base):
    __tablename__ = "software_versions"
    NA, UNKNOWN = 0, 1
    software_version_id = Col(Int, primary_key=True)
    code = Col(String)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    software_client_id = Col(Int, FK("software_clients.software_client_id"))
    software_client = relation(SoftwareClient)
    release_date = Col(DateTime)

class Sku(Base):
    __tablename__ = "skus"
    sku_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
        
class State(Base):
    __tablename__ = "states"
    INPROGRESS = 0
    SHIP = 10
    ERROR = 100
    CSHOLD = 110
    PENDING = 120
    WAIT = 140  # for 90 min. delay
    COMPLETE = 500
    CANCEL = 510
    VOID = 520
    UNKNOWN_OE_STATE = 530
    VOIDSHIP = 540
    COMMERCE_CANCEL = 550
    state_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)

class Theme(Base):
    __tablename__ = "themes"
    theme_id = Col(Int, primary_key=True)
    product_id = Col(Int, FK("products.product_id"))
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
        
class User(Base):
    __tablename__ = "users"
    AUTO, UNKNOWN, COMMERCE = range(1, 4)
    user_id = Col(Int, primary_key=True)
    username = Col(String)
    password = Col("passwd", String)
    first_name = Col(String)
    last_name = Col(String)
    start_date = Col(DateTime)
    termination_date = Col(DateTime)
    admin = Col(Int)
    badge_id = Col(String)
    active = Col(Int)
    permissions = relation("UserPermission",
                           primaryjoin=("User.user_id == "
                                        "UserPermission.user_id"))
    roles = relation("UserRole", primaryjoin="User.user_id == UserRole.user_id")
    @property
    def full_name(self):
        return str("%s %s" % (self.first_name, self.last_name)).strip()

class UserPermission(Base):
    __tablename__ = "user_permissions"
    user_id = Col(Int, FK("users.user_id"), primary_key=True)
    user = relation(User)
    permission_id = Col(Int, FK("permissions.permission_id"), primary_key=True)
    permission = relation(Permission)
    
class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Col(Int, FK("users.user_id"), primary_key=True)
    user = relation(User)
    role_id = Col(Int, FK("roles.role_id"), primary_key=True)
    role = relation(Role)
    
class Workflow(Base):
    __tablename__ = "workflows"
    workflow_id = Col(Int, primary_key=True)
    code = Col(String, unique=True)
    name = Col(String)
    description = Col(String)
    active = Col(Int)
    
class WorkflowItem(Base):
    __tablename__ = "workflow_items"
    workflow_item_id = Col(Int, primary_key=True)
    workflow_id = Col(Int, FK("workflows.workflow_id"))
    workflow = relation("Workflow")
    state_id = Col(Int, FK("states.state_id"))
    state = relation(State)
    batch_id = Col(Int, FK("batches.batch_id"))
    batch = relation(Batch)
    order_item_id = Col(Int, FK("order_items.order_item_id"))
    order_item = relation(OrderItem)
    product_item_id = Col(Int, FK("product_items.product_item_id"))
    product_item = relation(ProductItem)
    activity_id = Col(Int, FK("activities.activity_id"))
    activity = relation(Activity)
    user_id = Col(Int, FK("users.user_id"))
    user = relation(User)
    skip_activities = Col(String)
    work_date = Col(DateTime)
    created = Col(DateTime)
    last_updated = Col(DateTime)
    def __repr__(self):
        return ("<WorkflowItem('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', "
                "'%s'>" % (self.workflow_item_id, self.workflow_id,
                           self.batch_id, self.order_item_id,
                           self.product_item_id, self.activity_id,
                           self.user_id, self.state_id,
                           self.work_date))
                
