# Copyright (c) 2024, Fabric and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days
from flex.flex.doctype.payment_requisition.payment_requisition import PaymentRequisition

class TestPaymentRequisition(FrappeTestCase):
	def setUp(self):
		# Create test data
		self.series = frappe.get_all("Document Series", fields=["*"], limit=1)[0]
		self.company = frappe.get_all("Company", fields=["*"], limit=1)[0]
		self._create_test_employee()
		self._create_test_cost_center()
		self._create_test_expense_account()
		self.mode_of_payment = frappe.get_all("Mode of Payment", filters={"name": ["like", "cash"]}, fields=["*"], limit=1)[0]
		self._create_test_expense_item()

	def _create_test_employee(self):
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

	def _create_test_cost_center(self):
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

	def _create_test_expense_account(self):
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

	def _create_test_expense_item(self):
		if not frappe.db.exists("Expense Item", "Test Expense Item"):
			self.request_items = frappe.get_doc({
				"doctype": "Expense Item",
				"item_name": "Test Expense Item",
				"description": "This is a test expense item",
				"expense_account": self.expense_account.name,
				"payable_account": frappe.get_single("Payment Requisition Settings").default_payable_account,
				"use_default_payable_account": 0
			}).insert()
		else:
			self.request_items = frappe.get_doc("Expense Item", "Test Expense Item")

	def _create_test_supplier(self):
		"""Create a test supplier if it doesn't exist"""
		if not frappe.get_all("Supplier", filters={"supplier_name": "Test Supplier", "company": self.company.name}):
			self.supplier = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "Test Supplier",
				"supplier_group": "All Supplier Groups",
				"supplier_type": "Company",
				"company": self.company.name
			}).insert()
		else:
			self.supplier = frappe.get_all("Supplier", 
				filters={"supplier_name": "Test Supplier", "company": self.company.name})[0]

	def _create_payment_requisition(self, **kwargs):
		"""Create a test Payment Requisition with default or custom values"""
		default_values = {
			"doctype": "Payment Requisition",
			"date": today(),
			"series": self.series.name,
			"company": self.company.name,
			"party_type": "Employee",
			"party": self.employee.name,
			"currency": "USD",
			"cost_center": self.cost_center.name,
			"mode_of_payment": self.mode_of_payment.name,
			"request_items": [
				{
					"expense_item": self.request_items.name,
					"expense_account": self.expense_account.name,
					"cost_center": self.cost_center.name,
					"amount": 1000,
					"description": "Test Expense"
				}
			]
		}
		# Update default values with any custom values provided
		default_values.update(kwargs)
		return frappe.get_doc(default_values).insert()

	def _test_workflow_transitions(self, pr, transitions):
		"""Test a sequence of workflow transitions"""
		for from_state, to_state in transitions:
			pr.workflow_state = from_state
			pr.save()
			self.assertEqual(pr.workflow_state, from_state)
			
			pr.workflow_state = to_state
			pr.set("expense_items", [])
			pr.append("expense_items", {
				"expense_item": self.request_items.name,
				"expense_account": self.expense_account.name,
				"cost_center": self.cost_center.name,
				"amount": 1000,
				"description": "Test Expense"
			})
			pr.save()
			self.assertEqual(pr.workflow_state, to_state)

	def test_payment_requisition_creation(self):
		"""Test basic creation of Payment Requisition"""
		pr = self._create_payment_requisition()
		self.assertEqual(pr.total, 1000)
		self.assertEqual(pr.total_qty, 1)
		self.assertEqual(pr.workflow_state, "Quotations Required")

	def test_payment_requisition_workflow(self):
		"""Test all valid workflow transitions"""
		pr = self._create_payment_requisition()
		pr.payment_date = today()
		pr.reference = "TEST-REF-001" if self.mode_of_payment.name != "Cash" else None
		pr.save()
		# Test main workflow path
		main_transitions = [
			("Quotations Required", "Submitted to Accounts"),
			("Submitted to Accounts", "Pending Internal Check"),
			("Pending Internal Check", "Pending First Approval"),
			("Pending First Approval", "Pending Final Approval"),
			("Pending Final Approval", "Payment Due"),
			("Payment Due", "Capture Expenses"),
			("Capture Expenses", "Accounts Approval"),
			("Accounts Approval", "Closed")
		]
		self._test_workflow_transitions(pr, main_transitions)

		pr = self._create_payment_requisition()
		pr.payment_date = today()
		pr.reference = "TEST-REF-001" if self.mode_of_payment.name != "Cash" else None
		pr.save()
		# Test revision paths
		revision_transitions = [
			("Submitted to Accounts", "Employee Revision Required"),
			("Employee Revision Required", "Submitted to Accounts"),
			("Pending Internal Check", "Pending First Approval"),
			("Pending First Approval", "Pending Final Approval"),
			("Pending Final Approval", "Payment Due"),
			("Capture Expenses", "Accounts Approval"),
			("Accounts Approval","Expense Revision")
		]
		self._test_workflow_transitions(pr, revision_transitions)

		pr = self._create_payment_requisition()
		pr.payment_date = today()
		pr.reference = "TEST-REF-001" if self.mode_of_payment.name != "Cash" else None
		pr.save()
		# Test rejection and cancellation paths
		rejection_transitions = [
			("Submitted to Accounts", "Employee Revision Required"),
			("Employee Revision Required", "Submitted to Accounts"),
			("Pending Internal Check", "Pending First Approval"),
			("Pending First Approval", "Pending Final Approval"),
			("Pending Final Approval", "Rejected"),
			("Rejected", "Cancelled")
		]
		self._test_workflow_transitions(pr, rejection_transitions)

		# Ensure cancelled state is final
		with self.assertRaises(frappe.ValidationError):
			pr.workflow_state = "Payment Due"
			pr.save()

	def test_quotation_attachments(self):
		"""Test quotation attachment functionality"""
		pr = self._create_payment_requisition()
		
		# Test with incomplete quotations allowed
		pr.allow_incomplete_quotations = 1
		pr.save()
		self.assertEqual(pr.allow_incomplete_quotations, 1)

		# Test quotation attachments
		pr.first_quotation = "test_quotation_1.pdf"
		pr.second_quotation = "test_quotation_2.pdf"
		pr.third_quotation = "test_quotation_3.pdf"
		pr.save()

		self.assertEqual(pr.first_quotation, "test_quotation_1.pdf")
		self.assertEqual(pr.second_quotation, "test_quotation_2.pdf")
		self.assertEqual(pr.third_quotation, "test_quotation_3.pdf")

	def test_payment_journal_entry_creation(self):
		"""Test journal entry creation with different settings"""
		settings = frappe.get_single("Payment Requisition Settings")
		original_skip_payable = settings.skip_payable_journal_entry

		for skip_payable in [0, 1]:
			settings.skip_payable_journal_entry = skip_payable
			settings.save()

			pr = self._create_payment_requisition()
			
			# Move to Closed state
			workflow_states = [
				"Quotations Required",
				"Submitted to Accounts",
				"Pending Internal Check",
				"Pending First Approval",
				"Pending Final Approval",
				"Payment Due",
				"Capture Expenses",
				"Accounts Approval",
				"Closed"
			]

			# Add payment details
			pr.payment_date = today()
			pr.reference = "TEST-REF-001" if self.mode_of_payment.name != "Cash" else None

			pr.set("expense_items", [])
			pr.append("expense_items", {
				"expense_item": self.request_items.name,
				"expense_account": self.expense_account.name,
				"cost_center": self.cost_center.name,
				"amount": 1000,
				"description": "Test Expense"
			})
			pr.save()

			for state in workflow_states:
				pr.workflow_state = state
				pr.save()	

			# Verify journal entries
			if skip_payable == 1:
				if pr.party_type == "Employee":
					self.assertTrue(pr.payable_journal_entry)
				else:
					self.assertTrue(pr.expense_journal_entry)
					self.assertFalse(pr.payable_journal_entry)
			else:
				self.assertTrue(pr.expense_journal_entry)
				self.assertTrue(pr.payable_journal_entry)

			# Verify journal entry details
			je = frappe.get_doc("Journal Entry", pr.expense_journal_entry)
			if self.mode_of_payment.name != "Cash":
				self.assertEqual(je.cheque_no, pr.reference)
			self.assertEqual(je.total_debit, 1000)
			self.assertEqual(je.total_credit, 1000)

		# Restore original setting
		settings.skip_payable_journal_entry = original_skip_payable
		settings.save()

	def test_supplier_payment_requisition(self):
		"""Test Payment Requisition creation and workflow with Supplier as party"""
		self._create_test_supplier()
		
		# Create PR with supplier as party
		pr = self._create_payment_requisition(
			party_type="Supplier",
			party=self.supplier.name
		)
		
		self.assertEqual(pr.party_type, "Supplier")
		self.assertEqual(pr.total, 1000)
		
		# Test workflow transitions with supplier
		pr.payment_date = today()
		pr.reference = "TEST-REF-002" if self.mode_of_payment.name != "Cash" else None
		pr.save()
		
		# Test main workflow path for supplier
		supplier_transitions = [
			("Quotations Required", "Submitted to Accounts"),
			("Submitted to Accounts", "Pending Internal Check"),
			("Pending Internal Check", "Pending First Approval"),
			("Pending First Approval", "Pending Final Approval"),
			("Pending Final Approval", "Payment Due"),
			("Payment Due", "Capture Expenses"),
			("Capture Expenses", "Accounts Approval"),
			("Accounts Approval", "Closed")
		]
		self._test_workflow_transitions(pr, supplier_transitions)
		
		# Verify journal entries for supplier
		self.assertTrue(pr.expense_journal_entry)
		
		# Verify journal entry details
		je = frappe.get_doc("Journal Entry", pr.expense_journal_entry)
		self.assertEqual(je.total_debit, 1000)
		self.assertEqual(je.total_credit, 1000)

	def test_deposit_amount_calculation(self):
		"""Test deposit amount calculations and updates"""
		settings = frappe.get_single("Payment Requisition Settings")
		original_skip_payable = settings.skip_payable_journal_entry

		for skip_payable in [0, 1]:
			settings.skip_payable_journal_entry = skip_payable
			settings.save()
			pr = self._create_payment_requisition()
			
			# Initial state - total should be 1000 from the single request item
			self.assertEqual(pr.total, 1000)
			self.assertEqual(pr.total_expenditure, 0)
			self.assertEqual(frappe.utils.flt(pr.deposit_amount), 0)
			
			# Add an expense item for partial amount
			pr.append("expense_items", {
				"expense_item": self.request_items.name,
				"expense_account": self.expense_account.name,
				"cost_center": self.cost_center.name,
				"amount": 600,
				"description": "Partial Expense"
			})
			pr.save()
			
			# Verify total_expenditure updated
			self.assertEqual(pr.total_expenditure, 600)
			
			# Set deposit amount to remaining balance
			pr.deposit_amount = pr.total - pr.total_expenditure  # 1000 - 600 = 400
			pr.save()
			
			# Verify deposit amount
			self.assertEqual(pr.deposit_amount, 400)
			
			# Add another expense item
			pr.append("expense_items", {
				"expense_item": self.request_items.name,
				"expense_account": self.expense_account.name,
				"cost_center": self.cost_center.name,
				"amount": 300,
				"description": "Additional Expense"
			})
			pr.save()
			
			# Verify updated totals
			self.assertEqual(pr.total_expenditure, 900)
			
			# Update deposit amount to new remainder
			pr.deposit_amount = pr.total - pr.total_expenditure  # 1000 - 900 = 100
			pr.save()
			
			# Verify deposit amount updated
			self.assertEqual(pr.deposit_amount, 100)
			
			# Test when expenses exceed total
			pr.append("expense_items", {
				"expense_item": self.request_items.name,
				"expense_account": self.expense_account.name,
				"cost_center": self.cost_center.name,
				"amount": 200,
				"description": "Excess Expense"
			})
			pr.save()
			
			# Verify totals when expenses exceed request
			self.assertEqual(pr.total_expenditure, 1100)
			
			# Deposit amount should be 0 when expenses exceed total
			pr.deposit_amount = max(0, pr.total - pr.total_expenditure)
			pr.save()
			
			self.assertEqual(pr.deposit_amount, 0)

			pr.append("request_items", {
				"expense_item": self.request_items.name,
				"expense_account": self.expense_account.name,
				"cost_center": self.cost_center.name,
				"amount": 100,
				"description": "Excess Expense"
			})
			pr.save()

			# Move to Closed state
			workflow_states = [
				"Quotations Required",
				"Submitted to Accounts",
				"Pending Internal Check",
				"Pending First Approval",
				"Pending Final Approval",
				"Payment Due",
				"Capture Expenses",
				"Accounts Approval",
				"Closed"
			]

			# Add payment details
			pr.payment_date = today()
			pr.reference = "TEST-REF-001" if self.mode_of_payment.name != "Cash" else None

			pr.save()

			for state in workflow_states:
				pr.workflow_state = state
				pr.save()	

			# Verify journal entries
			if skip_payable == 1:
				if pr.party_type == "Employee":
					self.assertTrue(pr.payable_journal_entry)
				else:
					self.assertTrue(pr.expense_journal_entry)
					self.assertFalse(pr.payable_journal_entry)
			else:
				self.assertTrue(pr.expense_journal_entry)
				self.assertTrue(pr.payable_journal_entry)

			# Verify journal entry details
			je = frappe.get_doc("Journal Entry", pr.expense_journal_entry)
			if self.mode_of_payment.name != "Cash":
				self.assertEqual(je.cheque_no, pr.reference)
			self.assertEqual(je.total_debit, 1100)
			self.assertEqual(je.total_credit, 1100)

		# Restore original setting
		settings.skip_payable_journal_entry = original_skip_payable
		settings.save()
