# Copyright (c) 2024, Fabric and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PaymentRequisition(Document):
	@frappe.whitelist()
	def validate_workflow(self):			
		settings = frappe.get_single("Payment Requisition Settings")
		user = frappe.get_doc("User", frappe.session.user)

		self.workflow_validation(user)
		self.setup_details(settings, user)

		if self.workflow_state in ["Awaiting Internal Approval", "Ready for Submission"]:
			self.payment_date = None
			self.reference = None

		if self.workflow_state == "Approved":
			# create journal entry without payable entry
			je = self.make_journal_entry(settings, user)
			# self.payment_journal_entry = je.name
			self.approval_comment = None
			if not self.payment_date: # and self.docstatus == 0: 
				# make sure to validate payment reference and date correctly on the form
				self.payable_journal_entry = je.name
			elif self.payment_date:
				self.payment_journal_entry = je.name
				self.workflow_state = "Payment Completed"				
			
		elif self.workflow_state == "Cancelled":
			# cancel related journal entries
			self.before_cancel()
			if self.docstatus != 2:
				self.docstatus = 2
	
	def before_cancel(self):
		# cancel related journal entries

		journals = frappe.get_all('Journal Entry', filters={'bill_no': self.name, 'docstatus': 1}, limit=20)
		for journal in journals:
			frappe.db.set_value("Journal Entry", journal.name, "docstatus", 2)

		if self.workflow_state != "Cancelled":
			self.workflow_state = "Cancelled"
	
		frappe.db.commit()

	def make_journal_entry(self, settings, user):
		je = []

		if settings.skip_payable_journal_entry == 1:
			je = self.make_single_journal_entry(settings, user)
		else:
			# Determine the type of journal entry to create
			if not self.payment_date: # and self.docstatus == 0: 
				# make sure to validate payment reference and date correctly on the form
				je = self.make_payable_journal_entry(settings, user)
			elif self.payment_date:
				je = self.make_payment_journal_entry(settings, user)
		# frappe.errprint(je.as_dict())
		# return	
		
		je.insert()
		return je.submit()
	
	def make_payable_journal_entry(self, settings, user):
		# Preparing the JE for payable entry
		account_entries = {}

		# Group expense details by account key
		for detail in self.expenses:
			account_key = (
				detail.expense_account,
				detail.project,
				detail.cost_center,
				self.party_type,
				self.party,
			)
			
			if account_key in account_entries:
				account_entries[account_key]['debit_in_account_currency'] += float(detail.amount)
			else:
				account_entries[account_key] = {
					'debit_in_account_currency': float(detail.amount),
					'user_remark': str(detail.description),
					'account': detail.expense_account,
					'project': detail.project,
					'cost_center': detail.cost_center,
					'party_type': self.party_type,
					'party': self.party
				}

		# Group payable account details
		for detail in self.expenses:
			account_key = (
				detail.expense_payable_account,
				detail.project,
				detail.cost_center,
				self.party_type,
				self.party,
			)
			
			if account_key in account_entries:
				if 'credit_in_account_currency' in account_entries[account_key]:
					account_entries[account_key]['credit_in_account_currency'] += float(detail.amount)
				else:
					account_entries[account_key]['credit_in_account_currency'] = float(detail.amount)
					account_entries[account_key]['user_remark'] = 'Amount payable to supplier'
					account_entries[account_key]['account'] = detail.expense_payable_account
			else:
				account_entries[account_key] = {
					'credit_in_account_currency': float(detail.amount),
					'user_remark': 'Amount payable to supplier',
					'account': detail.expense_payable_account,
					'project': detail.project,
					'cost_center': detail.cost_center,
					'party_type': self.party_type,
					'party': self.party
				}

		# Prepare accounts list
		accounts = list(account_entries.values())

		# Create the journal entry document
		je = frappe.get_doc({
			'title': self.name + ' - Payable',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		})

		return je


	def make_payment_journal_entry(self, settings, user):
		# Preparing the JE: convert self details into JE account details
		account_entries = {}

		# Group expenses by account
		
		for detail in self.expenses:
			account_key = (
				detail.expense_payable_account,
				detail.project,
				detail.cost_center,
				self.party_type,
				self.party,
			)
			
			if account_key in account_entries:
				account_entries[account_key]['debit_in_account_currency'] += float(detail.amount)
			else:
				account_entries[account_key] = {
					'debit_in_account_currency': float(detail.amount),
					'user_remark': str(detail.description),
					'account': detail.expense_payable_account,
					'project': detail.project,
					'cost_center': detail.cost_center,
					'party_type': self.party_type,
					'party': self.party
				}

		# Finally, add the payment account detail
		if self.mode_of_payment != "Cash" and (not self.reference or not self.payment_date):
			frappe.throw(
				title="Enter Payment Reference",
				msg="Payment Reference and Date are Required for all non-cash payments."
			)

		pay_account = frappe.db.get_value('Mode of Payment Account', {
				'parent': self.mode_of_payment, 
				'company': self.company
			},
			'default_account'
		)
		if not pay_account or pay_account == "":
			frappe.throw(
				title="Account Required in Mode of Payment",
				msg="The selected Mode of Payment has no linked account."
			)

		# Prepare accounts list
		accounts = list(account_entries.values())
		
		# Add the payment entry
		accounts.append({
			'credit_in_account_currency': float(self.total),
			'user_remark': str(self.remarks),
			'account': pay_account,
			'cost_center': self.cost_center
		})

		# Create the journal entry document
		je = frappe.get_doc({
			'title': self.name + ' - Payment',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'cheque_date': self.payment_date,
			'reference_date': self.payment_date,
			'cheque_no': self.reference,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		})

		return je



	@frappe.whitelist()
	def workflow_validation(self, user):

		wrk_state_changed = self.has_value_changed("workflow_state")

		comment = None
		if self.approval_comment:
			comment = self.approval_comment

		if wrk_state_changed:
			if self.workflow_state not in ["Cancelled", "Rejected", "Revision Requested"]:
				comment = None
				
			self.append("approval_history", {
				"approver": user.name,
				"full_name": user.full_name,
				"approval_status": self.workflow_state,
				"comment": comment
			})

	def setup_details(self, settings, user):
		# add expenses up and set the total field
		# add default project and cost center to expense items

		total = 0
		count = 0
		expense_items = []

		
		for detail in self.expenses:
			total += float(detail.amount)        
			count += 1
			
			if not detail.project and self.project_name:
				detail.project = self.project_name

			if not detail.activity and self.activity:
				detail.activity = self.activity
			
			if not detail.cost_center and self.cost_center:
				detail.cost_center = self.cost_center

			expense_items.append(detail)

		self.expenses = expense_items

		if self.total != total:
			self.total = total
		if self.no_of_expense_items != count:
			self.no_of_expense_items = count

	def make_payment_journal_entry_old(self, settings, user):
		# Preparing the JE: convert self details into je account details
		accounts = []

		for detail in self.expenses:            

			accounts.append({  
				'debit_in_account_currency': float(detail.amount),
				'user_remark': str(detail.description),
				'account': detail.expense_payable_account,
				'project': detail.project,
				'cost_center': detail.cost_center,
				'party_type': self.party_type,
				'party': self.party
			})

		# finally add the payment account detail

		pay_account = ""

		# require payment reference if not mode of payment isnt cash
		if (self.mode_of_payment != "Cash" and (not 
			self.reference or not self.payment_date)):
			frappe.throw(
				title="Enter Payment Reference",
				msg="Payment Reference and Date are Required for all non-cash payments."
			)
		else:
			self.clearance_date = ""
			self.reference = ""


		pay_account = frappe.db.get_value('Mode of Payment Account', {'parent' : self.mode_of_payment, 'company' : self.company}, 'default_account')
		if not pay_account or pay_account == "":
			frappe.throw(
				title="Error",
				msg="The selected Mode of Payment has no linked account."
			)

		accounts.append({  
			'credit_in_account_currency': float(self.total),
			'user_remark': str(detail.description),
			'account': pay_account,
			'cost_center': self.cost_center
		})

		# create the journal entry
		je = frappe.get_doc({
			'title': self.name + ' - Payment',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'cheque_date': self.payment_date,
			'reference_date': self.payment_date,
			'cheque_no': self.reference,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		})		

		return je




	def make_single_journal_entry(self, settings, user):
		# Preparing the JE: convert self details into je account details
		accounts = []

		for detail in self.expenses:            

			accounts.append({  
				'debit_in_account_currency': float(detail.amount),
				'user_remark': str(detail.description),
				'account': detail.expense_account,
				'project': detail.project,
				'cost_center': detail.cost_center,
				'party_type': self.party_type,
				'party': self.party
			})

		# finally add the payment account detail

		pay_account = ""

		# require payment reference if not mode of payment isnt cash
		if (self.mode_of_payment != "Cash" and (not 
			self.reference or not self.payment_date)):
			frappe.throw(
				title="Enter Payment Reference",
				msg="Payment Reference and Date are Required for all non-cash payments."
			)
		else:
			self.clearance_date = ""
			self.reference = ""


		pay_account = frappe.db.get_value('Mode of Payment Account', {'parent' : self.mode_of_payment, 'company' : self.company}, 'default_account')
		if not pay_account or pay_account == "":
			frappe.throw(
				title="Error",
				msg="The selected Mode of Payment has no linked account."
			)

		accounts.append({  
			'credit_in_account_currency': float(self.total),
			'user_remark': str(detail.description),
			'account': pay_account,
			'cost_center': self.cost_center
		})

		# create the journal entry
		je = frappe.get_doc({
			'title': self.name,
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'cheque_date': self.payment_date or self.date,
			'reference_date': self.payment_date or self.date,
			'cheque_no': self.reference,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		})		

		return je

	def make_payable_journal_entry_draft(self, settings, user):
		# Preparing the JE for payable entry
		accounts = []

		# Add expense details
		for detail in self.expenses:
			accounts.append({
				'debit_in_account_currency': float(detail.amount),
				'user_remark': str(detail.description),
				'account': detail.expense_account,
				'project': detail.project,
				'cost_center': detail.cost_center
			})

		
		# accounts.append({
		# 	'credit_in_account_currency': float(self.total),
		# 	'user_remark': 'Amount payable to supplier',
		# 	'account': detail.expense_payable_account,
		# 	'cost_center': self.cost_center,
		# 	'party_type': self.party_type,
		# 	'party': self.party
		# })

		account_entries = {}

		# Add payable account details
		for detail in self.expenses:
			account_key = (
				detail.expense_payable_account,
				detail.project,
				detail.cost_center,
				self.party_type,
				self.party,
			)
			
			if account_key in account_entries:
				account_entries[account_key]['credit_in_account_currency'] += float(detail.amount)
			else:
				account_entries[account_key] = {
					'credit_in_account_currency': float(detail.amount),
					'user_remark': 'Amount payable to supplier',
					'account': detail.expense_payable_account,
					'project': detail.project,
					'cost_center': detail.cost_center,
					'party_type': self.party_type,
					'party': self.party
				}

		# Create the journal entry document
		je = frappe.get_doc({
			'title': self.name + ' - Payable',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		})

		return je
def ep(param):
	frappe.errprint(param)