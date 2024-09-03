# Copyright (c) 2024, Fabric and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days
from flex.flex.doctype.payment_requisition.payment_requisition import PaymentRequisition

class TestPaymentRequisition(FrappeTestCase):
	def setUp(self):
		# Create test data
		# company = frappe.get_all("Company", fields=["name"], limit=1)[0]
		self.series = frappe.get_all("Document Series", fields=["*"], limit=1)[0]
		self.company = frappe.get_all("Company", fields=["*"], limit=1)[0]

		if not frappe.get_all("Employee", filters={"first_name": "John", "last_name": "Doe", "company": self.company.name}):
			self.employee = frappe.get_doc({
				"doctype": "Employee",
				"first_name": "John",
				"last_name": "Doe",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"company": self.company.name
			}).insert()
		else:
			self.employee = frappe.get_all("Employee", filters={"first_name": "John", "last_name": "Doe", "company": self.company.name})[0]

		if not frappe.get_all("Cost Center", filters={"cost_center_name": "Test Cost Center", "company": self.company.name}):
			self.cost_center = frappe.get_doc({
				"doctype": "Cost Center",
				"cost_center_name": "Test Cost Center",
				"company": self.company.name,
				"parent_cost_center": self.company.name + " - " + self.company.abbr,
				"is_group": 0
			}).insert()
		else:
			self.cost_center = frappe.get_all("Cost Center", fields=["*"], filters={"cost_center_name": "Test Cost Center", "company": self.company.name})[0]

		if not frappe.get_all("Account", filters={"account_name": "Test Expense Account", "company": self.company.name}):
			self.expense_account = frappe.get_doc({
				"doctype": "Account",
				"account_name": "Test Expense Account",
				"parent_account": "5200 - Indirect Expenses - " + self.company.abbr,
				"company": self.company.name,
				"is_group": 0,
				"root_type": "Expense"
			}).insert()
		else:
			self.expense_account = frappe.get_all("Account", filters={"account_name": "Test Expense Account", "company": self.company.name})[0]

		if not frappe.get_all("Mode of Payment", filters={"mode_of_payment": "Test Payment Mode"}):
			self.mode_of_payment = frappe.get_doc({
				"doctype": "Mode of Payment",
				"mode_of_payment": "Test Payment Mode",
				"type": "Bank"
			}).insert()
		else:
			self.mode_of_payment = frappe.get_all("Mode of Payment", filters={"mode_of_payment": "Test Payment Mode"})[0]

		 # Create test Expense Item if it doesn't exist
		if not frappe.db.exists("Expense Item", "Test Expense Item"):
			self.expense_item = frappe.get_doc({
				"doctype": "Expense Item",
				"item_name": "Test Expense Item",
				"description": "This is a test expense item",
				"expense_account": self.expense_account.name,
				"payable_account": frappe.get_single("Payment Requisition Settings").default_payable_account,
				"use_default_payable_account": 0
			}).insert()
		else:
			self.expense_item = frappe.get_doc("Expense Item", "Test Expense Item")

	def tearDown(self):
		# Clean up test data
		frappe.set_user("Administrator")
		# frappe.delete_doc("Payment Requisition", frappe.get_last_doc("Payment Requisition").name)
		# frappe.delete_doc("Employee", self.employee.name)
		# frappe.delete_doc("Cost Center", self.cost_center.name)
		# frappe.delete_doc("Account", self.expense_account.name)
		# frappe.delete_doc("Mode of Payment", self.mode_of_payment.name)
		# frappe.delete_doc("Company", self.company.name)
		# frappe.delete_doc("Expense Item", self.expense_item.name)

	def test_payment_requisition_creation(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"company": self.company.name,
			"series": self.series.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"date": today(),
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": [
				{
					"expense_item": self.expense_item.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		})
		pr.insert()

		self.assertEqual(pr.total, 1000)
		self.assertEqual(pr.no_of_expense_items, 1)
		self.assertEqual(pr.workflow_state, "Draft")

	def test_payment_requisition_workflow(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"series": self.series.name,
			"company": self.company.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"date": today(),
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": [
				{
					"expense_item": self.expense_item.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		}).insert()

		# Test workflow states
		pr.workflow_state = "Submitted to Accounts"
		pr.save()
		self.assertEqual(pr.workflow_state, "Submitted to Accounts")

		# pr.workflow_state = "Ready for Submission"
		# pr.save()
		# self.assertEqual(pr.workflow_state, "Ready for Submission")

		pr.workflow_state = "Awaiting Internal Approval"
		pr.save()
		self.assertEqual(pr.workflow_state, "Awaiting Internal Approval")

		pr.workflow_state = "Awaiting Director Approval (1)"
		pr.save()
		self.assertEqual(pr.workflow_state, "Awaiting Director Approval (1)")

		pr.workflow_state = "Awaiting Director Approval (2)"
		pr.save()
		self.assertEqual(pr.workflow_state, "Awaiting Director Approval (2)")

		pr.workflow_state = "Approved"
		pr.save()
		self.assertEqual(pr.workflow_state, "Approved")

	def test_payment_requisition_currency_conversion(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"company": self.company.name,
			"party_type": "Employee",
			"series": self.series.name,
			"party": self.employee.name,
			"date": today(),
			"currency": "EUR",
			"conversion_rate": 1.2,
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": [
				{
					"expense_item": self.expense_item.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		}).insert()

		self.assertEqual(pr.total, 1000)
		self.assertEqual(pr.base_total, 1200)

	def test_payment_requisition_validation(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"series": self.series.name,
			"company": self.company.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"date": today(),
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": []
		})

		with self.assertRaises(frappe.ValidationError):
			pr.insert()

	def test_payment_requisition_gl_entry(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"series": self.series.name,
			"company": self.company.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"date": today(),
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": [
				{
					"expense_item": self.expense_item.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		}).insert()

		pr.submit()

		gl_entries = frappe.get_all("GL Entry", 
									filters={"voucher_type": "Payment Requisition", "voucher_no": pr.name},
									fields=["account", "debit", "credit"])

		self.assertEqual(len(gl_entries), 2)
		self.assertTrue(any(entry["account"] == self.expense_account.name and entry["debit"] == 1000 for entry in gl_entries))
		self.assertTrue(any(entry["account"].endswith("Payable - " + self.company.abbr) and entry["credit"] == 1000 for entry in gl_entries))

	def test_quotation_attachment(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"series": self.series.name,
			"company": self.company.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"date": today(),
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": [
				{
					"expense_item": self.expense_item.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		}).insert()

		# Test quotation attachment
		pr.first_quotation = "test_quotation_1.pdf"
		pr.second_quotation = "test_quotation_2.pdf"
		pr.third_quotation = "test_quotation_3.pdf"
		pr.save()

		self.assertEqual(pr.first_quotation, "test_quotation_1.pdf")
		self.assertEqual(pr.second_quotation, "test_quotation_2.pdf")
		self.assertEqual(pr.third_quotation, "test_quotation_3.pdf")

	def test_allow_incomplete_quotations(self):
		pr = frappe.get_doc({
			"doctype": "Payment Requisition",
			"series": self.series.name,
			"company": self.company.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"date": today(),
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"expenses": [
				{
					"expense_item": self.expense_item.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		}).insert()

		# Test allow_incomplete_quotations
		pr.allow_incomplete_quotations = 1
		pr.save()
		self.assertEqual(pr.allow_incomplete_quotations, 1)

		pr.allow_incomplete_quotations = 0
		pr.save()
		self.assertEqual(pr.allow_incomplete_quotations, 0)

if __name__ == '__main__':
	frappe.test.run_tests()