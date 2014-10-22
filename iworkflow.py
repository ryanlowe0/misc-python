# $Id: iworkflow.py 7888 2010-03-31 19:41:31Z ryan $

from datetime import datetime, timedelta

from sqlalchemy.orm.exc import NoResultFound

from plant.resources import res
from plant.dbengine import transactional
from plant.model import WorkflowItem, User, State


DEBUG = 0
DEBUG_SQL = 0
DEBUG_PROCESS = 0

FIRST_REORDER_ACTIVITY = 'push-jpeg'


class WorkflowError(Exception): pass
class WorkflowUpdateError(WorkflowError): pass
class WorkflowValidationError(WorkflowError): pass
class WorkflowActivityNotFound(WorkflowError): pass

class WorkflowInterface(object):

    def __init__ (self):
        self.config = res.conf
        self.workflowdef = self.config.workflowdef
        # store skip_activities for reference, and remove markers
        self.skip_activities = {}
        for w, steps in self.workflowdef.items():
            skip = [s.rstrip('*') for s in steps if s.endswith('*')]
            self.skip_activities[w] = skip
            self.workflowdef[w] = [s.rstrip('*') for s in steps]
        #self.updateCutoff()

        
    @transactional
    def createWorkflow(self, session, order_item_id):
        """Initializes workflow by creating a workflow item."""
        if DEBUG:
            print __name__, 'createWorkflow(%s)' % order_item_id
        workflow_code = self.getWorkflowByOrderItemId(order_item_id)
        orderitem = self.orders.getOrderItem(session, order_item_id)
        now = datetime.now()
        if orderitem.orig_order_item_id not in (order_item_id, None):
            activity_code = FIRST_REORDER_ACTIVITY
            user_id = User.AUTO
        else:
            activity_code = self.workflowdef[workflow_code][0]
            # if not a reorder add a product_item entry record too
            if orderitem.product_item_id: # gift-certs have no product_item
                self.histories.updateProductHistory(
                    session, orderitem.product_item_id, activity_code, now)
            user_id = User.COMMERCE
        self.histories.updateOrderHistory(session, order_item_id, 
                                          activity_code, now)
        work_date = orderitem.order.purchase_date
        if not work_date:
            raise WorkflowError("Unable to create workflow for order_item: "
                                "%s.  purchase_date is blank." % order_item_id)
        wi = WorkflowItem(workflow_id=self.workflows.getId(workflow_code),
                          order_item_id=order_item_id,
                          product_item_id=orderitem.product_item_id,
                          activity_id=self.activities.getId(activity_code),
                          state_id=State.INPROGRESS,
                          user_id=user_id,
                          skip_activities='',
                          created=now,
                          work_date=work_date)
        session.add(wi)
        workitem = self.getWorkflowItem(order_item_id)
        next = self.getNextActivity(session, workitem)
        workitem.activity_id = self.activities.getId(next)


    @transactional
    def setBatchId(self, session, order_item_id, batch_id):
        workitem = self.getWorkflowItem(order_item_id)
        workitem.batch_id = batch_id
        session.add(workitem)
        

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
                    raise WorkflowError('Only one entity_id may be provided')
                entity_id = id
                entity_name = name
        if not entity_name:
            raise WorkflowError('No valid entity_ids were provided')
        return entity_name, entity_id

    @transactional
    def updateWorkflow(self, session, activity_code, order_item_id=None, 
                       batch_id=None, product_item_id=None, user_id=User.AUTO, 
                       comments=None):
        """
        Update an existing workflow_item and history records. Workflow gets
        next activity and history writes the activity that has just finished.

        Identified by batch_id, order_item_id, or product_item_id.
        
        Raise Error if:
            - more or less than one id is given
            - entity_id is invalid for given activity

        Only update workflow item if validation passes
         (history is updated regardless)
        """
        try:
            entity_name, entity_id = self._getEntityId(order_item_id, 
                                                       batch_id, 
                                                       product_item_id)
        except WorkflowError, e:
            # convert to update error
            entity_id = order_item_id or batch_id or product_item_id
            raise WorkflowUpdateError('Not found: %s' % entity_id)
        entity_type = entity_name[:-3]  # strip _id
        if entity_name == 'order_item_id':
            workitem = self.getWorkflowItem(session, entity_id)
            self._updateWorkflowItem(session, activity_code, workitem, user_id)
        elif entity_name == 'product_item_id':
            orderitems = self.productItems.getProductItem(
                session, entity_id).order_items
            # loop through all order_items with given product_item_id
            for oi in orderitems:
                workitem = self.getWorkflowItem(session, oi.order_item_id)
                self._updateWorkflowItem(session, activity_code, 
                                         workitem, user_id)
        elif entity_name == 'batch_id':
            batchitems = self.batches.getBatch(session, entity_id).items
            # loop through all order_items with given batch_id
            for bi in batchitems:
                if not bi.active: continue
                workitem = self.getWorkflowItem(session, bi.order_item_id)
                self._updateWorkflowItem(session, activity_code, 
                                         workitem, user_id)
        # update history
        now = datetime.now()
        self.histories.updateHistory(session, entity_type, entity_id,
                                     activity_code, now, user_id, comments)

    @transactional
    def _updateWorkflowItem(self, session, activity_code, 
                            workitem, user_id=User.AUTO):
        """Update workflow_item record for a single order_item_id.
        
           If activity is a skip activity, record to skip_activities
           if not already there, otherwise raise Exception
           
           Return whether or not item was updated.
        """
        activity_id = self.activities.getId(activity_code)
        if activity_id <> workitem.activity_id:
            msg = 'Current and update activities do not match'
            raise WorkflowValidationError(msg)
        # get next activity
        activity_code = self.getNextActivity(session, workitem)
        if activity_code:
            workitem.activity_id = self.activities.getId(activity_code)
        else:   # finishing last activity
            workitem.state_id = State.COMPLETE
        workitem.user_id = user_id
        if activity_code in self.skip_activities[workitem.workflow.code]:
            if activity_code in workitem.skip_activities:
                raise WorkflowUpdateError('Attempting to repeat a one-time '
                                          'action.')
            elif workitem.skip_activities:
                workitem.skip_activities += ',' + activity_code
            else:
                workitem.skip_activities += activity_code
        session.add(workitem)
        return True


    @transactional
    def errorWorkflow(self, session, order_item_id=None, batch_id=None, 
                      product_item_id=None, user_id=User.AUTO, comments=None):
        """Puts all workflow items that match given order_item, batch, 
           or product_item id into error hold state.

           Also, records error to history.
        """
        try:
            entity_name, entity_id = self._getEntityId(order_item_id, 
                                                       batch_id, 
                                                       product_item_id)
        except WorkflowError, e:
            # convert to update error
            raise WorkflowUpdateError('Unable to update to %s state: %s' % 
                                      (activity_code, e))
        workitems = self.getWorkItems(session, order_item_id, 
                                      batch_id, product_item_id)
        entity_type = entity_name[:-3]
        for wi in workitems:
            wi.state_id = State.ERROR
            wi.user_id = user_id
            session.add(wi)
        # update history
        now = datetime.now()
        self.histories.updateHistory(session, entity_type, entity_id, 'error',
                                     now, user_id, comments)
        
    @transactional
    def setState(self, session, state_id, order_item_id=None, batch_id=None,
                product_item_id=None):
        """Set workflow item's state_id for a given id.

           If trying to unerror an order item in a batch state, 
           set state_id for entire batch instead.
        
           Return list of order_item_ids altered.
        """
        orders = []
        for wi in self.getWorkItems(session, order_item_id, 
                                    batch_id, product_item_id):
            if batch_id is None and state_id == State.INPROGRESS and \
               self.activities.get(wi.activity_id)['entity_type'] == 'batch':
                return self.setState(session, state_id, batch_id=wi.batch_id)
            wi.state_id = state_id
            orders.append(wi.order_item_id)
            session.add(wi)
        return orders
    
    @transactional
    def unError(self, session, order_item_id=None, batch_id=None,
                product_item_id=None):
        """Clear errors for all workflow items for given id"""
        return self.setState(session, State.INPROGRESS, order_item_id, 
                             batch_id, product_item_id)
    
    @transactional
    def getWorkItems(self, session, order_item_id=None, batch_id=None,
                     product_item_id=None):
        entity_name, entity_id = self._getEntityId(order_item_id, batch_id, 
                                                   product_item_id)
        attr = getattr(WorkflowItem, entity_name)
        return session.query(WorkflowItem).filter(attr == entity_id).all()


    @transactional
    def getOrdersToProcess(self, session, activity_code):
        """Find entity_ids across all workflows with given activity_code.
        
           If activity is a skip_activity, only return if not present in
           skip_activity field.
        """
        activity_id = self.activities.getId(activity_code)
        query = session.query(WorkflowItem).filter(
            (WorkflowItem.activity_id == activity_id) &
            (WorkflowItem.state_id == State.INPROGRESS))
        if activity_code in self.skip_activities:
            query = query.filter(~WorkflowItem.skip_activities
                                 .like('%%%s%%' % activity_code))
        if activity_code == 'order-release':
            # special case additional constaint on elapsed time
            try:
                delay = self.config.manufacturing.delay_minutes
            except KeyError, e:
                raise WorkflowError('Missing required config: '
                                    'manufacturing.delay_minutes')
            delay_date = datetime.now() - timedelta(minutes=int(delay))
            query = query.filter(WorkflowItem.work_date <= delay_date)
        # get entity ids
        items = []
        entity_name = self.activities.get(activity_id)['entity_type']
        for r in query.all():
            id = r[entity_name + '_id']
            if id and id not in items:
                items.append(id)
        return items


    @transactional
    def getNextActivity(self, session, workitem):
        workflow_code = self.workflows.getCode(workitem.workflow_id)
        static_workflow = self.workflowdef[workflow_code]
        activity_code = self.activities.getCode(workitem.activity_id)
        try:
            next = static_workflow[static_workflow.index(activity_code) + 1]
        except IndexError:  # no activity after the last one
            next = ''
        return next

    
    @transactional
    def validateActivity(self, session, order_item_id, activity):
        """Validate whether given activity = current workflow activity, 
           and whether workflow/order_item are in proper states.

           If activity is None, bypass activity check
        """
        workitem = self.getWorkflowItem(session, order_item_id)
        try:
            workflow_code = self.workflows.getCode(workitem.workflow_id)
            static_workflow = self.workflowdef[workflow_code]
        except:
            static_workflow = []
        try:
            orderitem = self.orders.getOrderItem(session, order_item_id)
        except:
            orderitem = None
        msg = ''
        if not orderitem:
            msg = 'Order not found'
        elif orderitem.state_id in (State.SHIP, State.COMPLETE):
            msg = '*%s* has already shipped' % order_item_id
        elif orderitem.state_id in (State.VOID, State.CANCEL, 
                                    State.COMMERCE_CANCEL):
            msg = '*%s* has been cancelled. Please discard.' % order_item_id
        elif not workitem:
            msg = 'No workflow item found for *%s*' % order_item_id
        elif activity is not None and activity not in static_workflow:
            msg = 'Unknown activity *(%s)*' % activity
        elif workitem.state_id == State.ERROR:
            msg = "*%s* is in *ERROR*. Please inform your supervisor." % \
                  order_item_id
        elif workitem.state_id == State.CSHOLD:
            msg = '*%s* has been put on hold by customer service.' % \
                  order_item_id
        elif activity in (workitem.workflow.code, None):
            msg = '*%s* is not in a valid state *(%s)*' % (order_item_id, 
                                                           activity)
        if msg:
            raise WorkflowValidationError(msg)


    @transactional
    def getWorkflowItem(self, session, order_item_id):
        """Returns workflowItem associated with given order item"""
        try:
            return session.query(WorkflowItem).filter_by(
                order_item_id=order_item_id).one()
        except NoResultFound:
            return None


    @transactional
    def getWorkflowByOrderItemId(self, session, order_item_id):
        """Find appropriate static workflow_code for a given order_item_id"""

        order_item = self.orders.getOrderItem(session, order_item_id)
        order_type = order_item.order_type
        product = order_item.product.code
        if order_type in ('giftcert', 'share'):
            code = order_type
        elif product in ('classic', 'deluxe'):
            cover_type = order_item.feature.cover_type.code
            if cover_type == 'pw':
                code = 'diecut'
            elif cover_type == 'bj':
                code = 'jacketed'
            elif cover_type == 'pf':
                code = 'photofinish'
            else:
                raise ValueError('Could not find workflow for order_item %s' %
                                 order_item_id)
        elif product.endswith('_cj'):
            code = 'jacketonly'
        elif product.endswith('card'):
            code = 'card'
        elif product in ('pocket', 'calendar'):
            code = product
        else:
            raise ValueError('Could not find workflow for order_item %s' %
                             order_item_id)
        return code

    @transactional
    def getWorkflowIdByOrderItemId(self, session, order_item_id):
        """Find appropriate static workflow_id for a given order_item_id"""
        code = self.getWorkflowByOrderItemId(session, order_item_id)
        return self.workflows.getId(code)

    def updateCutoff(self):
        """Read and process config parameters:
              cutoff_foid          - eq. 1495996
              cutoff_time          - eq. 2009-10-30 06:56
              shipping_ext_time    - eq. 2009-10-31 17:56
              shipping_ext_methods - eq. 03,05
              shipping_ext_promos  - eq. 212DEC21,FREESHIP20              
           Behavior:
              Sets: self.cutoff_time  - Earliest of cutoff_foid, and
                                        cutoff_time
                    self.shipping_ext - timedelta from self.cutoff_time
                    self.shipping_ext_methods - a list
                    self.shipping_ext_promos - a list
        """
        # Get cutoff datetime or foid, covert to datetime, use earliest
        try:    
            foid = eval(str(self.config.manufacturing.get('cutoff_foid')))
            t = self.orders.getOrder(foid).order_date
            if not isinstance(t, datetime):
                t = datetime(*map(int, t.tuple()[:6]))
            self.cutoff_time = t
        except: 
            self.cutoff_time = None        
        c = self.config.manufacturing.get('cutoff_time')
        try:
            t = datetime(*strptime(c, '%Y-%m-%d %H:%M')[:6])
            if self.cutoff_time:
                self.cutoff_time = min(self.cutoff_time, t)
            else:
                self.cutoff_time = t
        except: 
            pass
        # Get shipping extension hours and supported methods        
        c = self.config.manufacturing.get('shipping_ext_time')
        try:    
            t = datetime(*strptime(c, '%Y-%m-%d %H:%M')[:6])
        except: 
            t = self.cutoff_time
        if self.cutoff_time:
            self.shipping_ext = max(timedelta(seconds=0), t - self.cutoff_time)
        else:
            self.shipping_ext = None
        c = self.config.manufacturing.get('shipping_ext_methods')
        self.shipping_ext_methods = c.split(',') if c else []
        
        c = self.config.manufacturing.get('shipping_ext_promos')
        self.shipping_ext_promos = c.split(',') if c else []

    @property
    def activities(self):
        if '_activities' not in self.__dict__:
            from controllers.attributes import Attributes
            self._activities = Attributes('Activity')
        return self._activities

    @property
    def batches(self):
        if '_batches' not in self.__dict__:
            from controllers.batches import Batches
            self._batches = Batches()
        return self._batches

    @property
    def histories(self):
        if '_histories' not in self.__dict__:
            from controllers.histories import Histories
            self._histories = Histories()
        return self._histories

    @property
    def orders(self):
        if '_orders' not in self.__dict__:
            from controllers.orders import Orders
            self._orders = Orders()
        return self._orders

    @property
    def productItems(self):
        if '_productitems' not in self.__dict__:
            from controllers.productitems import ProductItems
            self._productitems = ProductItems()
        return self._productitems

    @property
    def workflows(self):
        if '_workflows' not in self.__dict__:
            from controllers.attributes import Attributes
            self._workflows = Attributes('Workflow')
        return self._workflows


