# Copyright (c) 2024, Fabric and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeExpenseTracker(Document):
    def validate(self):
        self.setup_expense_details()

    @frappe.whitelist()
    def get_dashboard_data(self):
        if self.payment_requisition:
            doc = frappe.get_cached_doc("Payment Requisition", self.payment_requisition)
            return {
                "total_allocated": doc.total,
                "total_expenditure": doc.total_expenditure
            }
        return {
            "total_allocated": 0,
            "total_expenditure": 0
        }

    
    def setup_expense_details(self):
        # add expenses up and set the total field
        # add default project and cost center to expense items

        total = 0
        count = 0
        expense_items = []

        
        for detail in self.expenses:
            total += float(detail.amount)        
            count += 1
            
            if not detail.project and self.project:
                detail.project = self.project

            if not detail.activity and self.activity:
                detail.activity = self.activity
            
            if not detail.cost_center and self.cost_center:
                detail.cost_center = self.cost_center

            expense_items.append(detail)

        self.expenses = expense_items

        if self.total != total:
            self.total = total
        if self.total_qty != count:
            self.total_qty = count

def update_totals():
    super.setup_expense_details()