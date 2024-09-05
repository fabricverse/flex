# Copyright (c) 2024, Fabric and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PaymentRequisition(Document):
	def autoname(self):
		self.name = self.generate_custom_name()
	
	def after_insert(self):
		self.db_set("allow_incomplete_quotations", 0)
		self.notify_update()
	
	def after_save(self):
		pass
		# if self.workflow_state in ["Quotations Required", "Submitted to Accounts", "Ready for Submission"]:
		# 	if self.allow_incomplete_quotations == 0 and (not self.first_quotation or not self.second_quotation or not self.third_quotation):
		# 		frappe.throw("Please upload all quotations or tick the <strong>Allow Incomplete Quotations</strong> checkbox. " + str(self.allow_incomplete_quotations))
	
	@frappe.whitelist()
	def apply_workflow(self, user):
	
		if len(self.expenses) < 1:
			return
		settings = frappe.get_single("Payment Requisition Settings")

		self.setup_expense_details(settings, user)

		if self.workflow_state in ["Awaiting Internal Approval"]:
			self.payment_date = None
			self.reference = None

		if self.workflow_state == "Approved" and not self.payable_journal_entry:
			if settings.skip_payable_journal_entry == 0:
				# Create payable journal entry
				je = self.make_payable_journal_entry(settings, user)
				je.insert()
				je.submit()
				self.payable_journal_entry = je.name
			self.approval_comment = None				
			
		elif self.workflow_state == "Cancelled":
			# cancel related journal entries
			self.before_cancel()
			if self.docstatus != 2:
				self.docstatus = 2

	def on_change(self):
		if self.payment_journal_entry: return

		if self.workflow_state == "Approved" and self.payment_date:
			settings = frappe.get_single("Payment Requisition Settings")
			user = frappe.get_doc("User", frappe.session.user)

			if self.mode_of_payment == "Cash" or (self.mode_of_payment != "Cash" and self.reference):
				self.create_payment_journal_entry(settings, user)
				
			elif not self.reference:
				frappe.throw("{} is required for non-cash payments.".format(frappe.bold("Payment Reference")))

		if self.workflow_state == "Approved" and self.docstatus == 0:
			self.submit()	
		

	def create_payment_journal_entry(self, settings, user):
		if settings.skip_payable_journal_entry == 1:
			# Create single journal entry for both expense and payment
			je = self.make_single_journal_entry(settings, user)
		else:
			# Create payment journal entry
			je = self.make_payment_journal_entry(settings, user)
		
		je.insert()
		je.submit()

		self.db_set({
			"payment_journal_entry": je.name,
			"workflow_state": "Payment Completed"
		})
		frappe.db.commit()


	def apply_signature(self, user):
		"""
		Apply signature to the document, i.e signer name according to their input
			- cancel: cancelled by {signer}
			- approve: approver name {signer}
		"""
		pass

	def check_attachments(self, user):
		"""
		1st: wf state = attach docs
			- if no attachments, indicate message
			- warn if there are not quotations: you have not uploaded any quotations
			- if attachments, go to accounts for checking: wf action = submit to accounts
				- initiated by {user.full_name}
				- submitted without quotations
				- submitted with quotations
		2nd: wf state = submitted to accounts
			- quotations required by accounts user: wf state = submitted to accounts
			- next action:  submit for internal approval
		


		"""
		is_accounts_user = self.user_has_role(user, "Accounts User")
		# go straight to attach docs workflow state, otherwise go to awaiting internal approval


	def user_has_role(self, user, roles):
		user_roles = frappe.get_roles(user.name)
		for role in roles:
			if role in user_roles:
				return True
		return False

	def workflow_log(self, user):

		workflow_changed = self.has_value_changed("workflow_state")
		if workflow_changed:					
			self.append("approval_history", {
				"approver": user.name,
				"full_name": user.full_name,
				"approval_status": self.workflow_state,
				"comment": self.approval_comment
			})

		if self.workflow_state not in ["Approved", "Payment Completed"]:
			self.approval_comment = None
		
		# self.update_signatories(user)

	def validate(self):		
		user = frappe.get_doc("User", frappe.session.user)
		self.apply_workflow(user)

		
		# frappe.errprint(self.workflow_state + " " + str("update_signatories"))
		
		if self.docstatus == 0 and self.workflow_state in ["Submitted to Accounts", "Quotations Required", "Revision Requested", "Employee Revision Required"]:
			# frappe.errprint(self.workflow_state + " " + str("Pending"))
			if not self.raised_by:
				owner = frappe.get_doc("User", self.owner)
				self.raised_by = owner.full_name

			self.submitted_by = "Pending"
			self.checked_by = "Pending"
			self.initial_approver = "Pending"
			self.final_approver = "Pending"

		if self.workflow_state in ["Quotations Required", "Submitted to Accounts", "Ready for Submission"]:
			# if self.allow_incomplete_quotations == 0 and not self.first_quotation or not self.second_quotation or not self.third_quotation:
			# 	frappe.throw("Please upload all quotations or specify that incomplete quotations are allowed.")

			if self.user_has_role(user, ["Accounts User", "Accounts Manager"]) and self.submitted_by == "Pending":
				self.submitted_by = user.full_name
				

		if self.workflow_state in ["Ready for Submission", "Awaiting Internal Approval",]:
			if not self.submitted_by or self.submitted_by != user.full_name:
				self.submitted_by = user.full_name

		if self.workflow_state == "Awaiting Director Approval (1)":
			self.checked_by = user.full_name

		if self.workflow_state == "Awaiting Director Approval (2)":
			self.initial_approver = user.full_name
			
		if self.workflow_state == "Approved":
			self.final_approver = user.full_name

		# frappe.msgprint(self.workflow_state + " user: " + user.full_name)
		# print(self.workflow_state + " user: " + user.full_name)
		# frappe.db.cmmit()
		self.workflow_log(user)

		
		



	def setup_expense_details(self, settings, user):
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
				'party': self.party,
				'reference_name': self.name,
				'reference_type': 'Payment Requisition'
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
			'cost_center': self.cost_center,
			'reference_name': self.name,
			'reference_type': 'Payment Requisition'
		})

		# create the journal entry
		je_data = {
			'title': self.name + ' - Payment',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		}

		# add cheque no and date if mode of payment is not cash
		if self.mode_of_payment != "Cash":
			je_data.update({
				'cheque_date': self.payment_date,
				'reference_date': self.payment_date,
				'cheque_no': self.reference
			})

		je = frappe.get_doc(je_data)

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
				'party': self.party,
				'reference_name': self.name,
				'reference_type': 'Payment Requisition'
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
			'cost_center': self.cost_center,
			'reference_name': self.name,
			'reference_type': 'Payment Requisition'
		})

		# create the journal entry
		je_data = {
			'title': self.name + ' - Payment',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		}

		# add cheque no and date if mode of payment is not cash
		if self.mode_of_payment != "Cash":
			je_data.update({
				'cheque_date': self.payment_date,
				'reference_date': self.payment_date,
				'cheque_no': self.reference
			})

		je = frappe.get_doc(je_data)

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
				'cost_center': detail.cost_center,
				'reference_name': self.name,
				'reference_type': 'Payment Requisition'
			})
			
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


	def generate_custom_name(self):
		# get last transaction with similar prefix and increment the number
		# if none create this as first entry
		if not self.series:
			frappe.throw("{} is required.".format(frappe.bold("Series")))

		last_transaction = frappe.get_all('Payment Requisition', 
			filters={'name': ['like', f'{self.series}%']}, 
			order_by='creation desc',
			limit=1)

		year = frappe.utils.nowdate().split('-')[0]

		prefix = self.series.upper() + '-' + self.currency + '-' + year + '-'
		
		if last_transaction:
			number = int(last_transaction[0].name.split('-')[-1]) + 1
		else:
			number = 1

		number = str(number).zfill(4)		
		name = prefix + number

		return name

	def before_cancel(self):
		# cancel related journal entries

		journals = frappe.get_all('Journal Entry', filters={'bill_no': self.name, 'docstatus': 1}, limit=20)
		for journal in journals:
			frappe.db.set_value("Journal Entry", journal.name, "docstatus", 2)

		if self.workflow_state != "Cancelled":
			self.workflow_state = "Cancelled"
	
		frappe.db.commit()

	def make_journal_entry(self, settings, user):
		pass # todo: remove def
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
			'cost_center': self.cost_center,
			'reference_name': self.name,
			'reference_type': 'Payment Requisition'
		})

		# create the journal entry
		je_data = {
			'title': self.name + ' - Payment',
			'doctype': 'Journal Entry',
			'voucher_type': 'Journal Entry',
			'posting_date': self.date,
			'company': self.company,
			'accounts': accounts,
			'user_remark': self.remarks,
			'mode_of_payment': self.mode_of_payment,
			'pay_to_recd_from': self.party,
			'bill_no': self.name
		}

		# add cheque no and date if mode of payment is not cash
		if self.mode_of_payment != "Cash":
			je_data.update({
				'cheque_date': self.payment_date,
				'reference_date': self.payment_date,
				'cheque_no': self.reference
			})

		je = frappe.get_doc(je_data)

		return je


def ep(param):
	frappe.errprint(param)