# Copyright (c) 2024, Fabric and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExpenseItem(Document):
	@frappe.whitelist()
	def doc_setup(self):
		
		default_payable_account = self.get_default_payable_account()

		if not default_payable_account:
			self.use_default_payable_account = 0
			return
		self.payable_account = default_payable_account

	@frappe.whitelist()
	def set_default_account(self):		
		default_payable_account = self.get_default_payable_account()

		if default_payable_account and not self.default_payable_account:
			self.default_payable_account = default_payable_account

	def get_default_payable_account(self):
		settings = frappe.get_doc("Payment Requisition Settings", "Payment Requisition Settings")

		return settings.default_payable_account
