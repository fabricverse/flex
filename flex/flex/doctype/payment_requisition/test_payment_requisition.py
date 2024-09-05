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

		self.mode_of_payment = frappe.get_all("Mode of Payment", filters={"name": ["like", "cash"]}, fields=["*"], limit=1)[0]

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
		self.assertEqual(pr.workflow_state, "Quotations Required")

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

	# todo: combine with test_payment_requisition_workflow or refactor to payable
	"""def test_payment_requisition_gl_entry(self): 
		
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
		print(pr.workflow_state)


		gl_entries = frappe.get_all("GL Entry", 
									filters={"voucher_no": pr.name},
									fields=["account", "debit", "credit"])

		self.assertEqual(len(gl_entries), 2) # todo
		# self.assertTrue(any(entry["account"] == self.expense_account.name and entry["debit"] == 1000 for entry in gl_entries))
		# self.assertTrue(any(entry["account"].endswith("Payable - " + self.company.abbr) and entry["credit"] == 1000 for entry in gl_entries))
"""
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

	def test_payment_journal_entry_creation(self):
		# Get the current setting
		settings = frappe.get_single("Payment Requisition Settings")
		original_skip_payable = settings.skip_payable_journal_entry

		# Test both cases: with and without skipping payable journal entry
		for skip_payable in [0, 1]:
			settings.skip_payable_journal_entry = skip_payable
			settings.save()

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

			# pr.submit()
			# pr.reload()

			# Move the PR to Approved state
			workflow_states = [
				"Submitted to Accounts",
				"Awaiting Internal Approval",
				"Awaiting Director Approval (1)",
				"Awaiting Director Approval (2)",
				"Approved"
			]

			for state in workflow_states:
				pr.workflow_state = state
				pr.save()
				self.assertEqual(pr.workflow_state, state)
			# pr.reload()
			
			self.assertEqual(pr.workflow_state, "Approved")


			# Add payment date and reference
			pr.payment_date = today()
			pr.reference = "TEST-REF-001"
			pr.save()
			# pr.reload()
			
			self.assertTrue(pr.payment_date)
			if self.mode_of_payment.name != "Cash":
				self.assertTrue(pr.reference)

	
			self.assertEqual(pr.workflow_state, "Payment Completed")
			
			if skip_payable == 1:
				self.assertFalse(pr.payable_journal_entry)
			else:
				self.assertTrue(pr.payment_journal_entry)
				self.assertTrue(pr.payable_journal_entry)
				

			self.assertEqual(pr.workflow_state, "Payment Completed")
			self.assertTrue(pr.payment_journal_entry)

			# Verify the created journal entry
			je = frappe.get_doc("Journal Entry", pr.payment_journal_entry)
			
			if self.mode_of_payment.name != "Cash":
				print(self.mode_of_payment.name, je.cheque_no, pr.reference)
				self.assertEqual(je.cheque_no, pr.reference)
				
			self.assertEqual(je.total_debit, 1000)
			self.assertEqual(je.total_credit, 1000)

			# Check the number of journal entries created
			journal_entries = frappe.get_all("Journal Entry", filters={"bill_no": pr.name})
			expected_je_count = 1 if skip_payable else 2
			self.assertEqual(len(journal_entries), expected_je_count)

			# # Clean up
			# for je_name in [entry.name for entry in journal_entries]:
			# 	je = frappe.get_doc("Journal Entry", je_name)
			# 	je.cancel()
			# 	# frappe.delete_doc("Journal Entry", je.name)

			# pr.cancel()
			# frappe.delete_doc("Payment Requisition", pr.name)

		# Restore original setting
		settings.skip_payable_journal_entry = original_skip_payable
		settings.save()

# if __name__ == '__main__':
# 	frappe.test.run_tests()