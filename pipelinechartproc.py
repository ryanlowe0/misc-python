from ordersummaryproc import OrderSummaryProc
from plant.model import WorkflowItem, OrderItem

products = ("classic_pw", "pocket", "deluxe_pw", "classic_bj", "deluxe_bj",
            "postcard", "card", "calendar", "classic_cj", "deluxe_cj")

# Email related states are excluded from the list as are old states and those
# not part of the workflow.
states = ["Error", "CS Hold", "Entry", "Pull PDF", "Gen JPEG", "Push JPEG",
          "Order Release", "Release", "Batch Add", "Impose", "Impose Jacket",
          "Batch Imp", "Queue Print", "Queue Print Batch", "RIP",
          "Queue Press", "Press Load", "Manifest", "Batch Manifest", "Printed",
          "Cut", "Envelope", "QA 1", "QA 2", "Print Jacket", "QA Jacket",
          "QA Photo Finish", "Pack"]

class PipelineChartProc(object):
    """Gathers data for the various pipeline related charts that show progress
    through the workflow for all products."""
    
    def _appendAggregate(self, rows, product, state, chart_type, product_data):
        """Append the aggregate for the requested product / state combo to
        the list of data for the current product."""
        for row in rows:
            if (str(row.product_code) == product and
                str(row.activity) == state):
                if chart_type == "order":
                    product_data.append(int(row.orders))
                else:
                    product_data.append(int(row.units))
                break        
        else:
            product_data.append(0)

    def _appendSummedAggregate(self, rows, product, chart_type, product_data):
        """Append sum of the aggregates for the requested product to the list
        of data for the current product."""
        product_data.append(0)
        for row in rows:
            if str(row.product_code) == product:
                if chart_type == "order":
                    product_data[-1] += int(row.orders)
                else:
                    product_data[-1] += int(row.units)
                        
    def getData(self, chart_type):
        """Retrieve the aggregated data for the requested chary type."""    
        if chart_type == "order":
            facts = ["orders"]
        else:
            facts = ["units"]

        dimensions = ["activity", "product_code"]

        osp = OrderSummaryProc()

        # active rows
        filters = [(WorkflowItem.state_id.in_([0, 140]))]
        rows = osp.getData(facts, dimensions, filters)

        # cs-holds
        filters = [(WorkflowItem.state_id == 110)]
        hold_rows = osp.getData(facts, dimensions, filters)
    
        # errors
        filters = [(WorkflowItem.state_id == 100)]
        error_rows = osp.getData(facts, dimensions, filters)
        
        results = [] # 1 row for each product with each state as a col
        for product in products:
            product_data = []        
            for state in states:
                if state == "Error":
                    self._appendSummedAggregate(error_rows, product,
                                                chart_type, product_data)
                elif state == "CS Hold":
                    self._appendSummedAggregate(hold_rows, product,
                                                chart_type, product_data)
                else:
                    self._appendAggregate(rows, product, state, chart_type,
                                          product_data)
            results.append(product_data)        
        return results
