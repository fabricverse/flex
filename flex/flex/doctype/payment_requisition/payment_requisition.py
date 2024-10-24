# Copyright (c) 2024, Fabric and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


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
    def apply_workflow(self, user): # update
        # if self.workflow_state == "Quotations Requireds":
        if self.workflow_state in ["Quotations Required", "Submitted to Accounts", "Awaiting Internal Approval"]:
            if self.workflow_state == "Quotations Required" and self.workflow_state != "Submitted to Accounts":
                self.workflow_state = "Submitted to Accounts"
                self.save()
            self.workflow_state = "Awaiting Internal Approval"
            self.save()
            self.workflow_state = "Awaiting Director Approval (1)"
            self.save()
            self.workflow_state = "Awaiting Director Approval (2)"
            self.save()
            self.workflow_state = "Payment Due"
            self.save()

        if len(self.request_items) < 1:
            return
        settings = frappe.get_single("Payment Requisition Settings")

        self.setup_expense_details(settings, user)

        if self.workflow_state in ["Awaiting Internal Approval"]:
            self.payment_date = None
            self.reference = None

        # if self.workflow_state == "Approved" and not self.payable_journal_entry: # update
        if self.workflow_state == "Capture Expenses": #in ["Payment Due"]:
            
            # Create payable journal entry
            if self.party_type == "Employee":
                je = self.make_employee_advance_je()
            else:
                if settings.skip_payable_journal_entry == 0:
                    je = self.make_payable_journal_entry()
            if je:
                je.insert()
                je.submit()

                self.payable_journal_entry = je.name
                self.approval_comment = None
        elif self.workflow_state == "Closed":
            if self.party_type == "Employee":
                je = self.make_employee_expense_je()
            else:
                if settings.skip_payable_journal_entry == 1:
                    je = self.make_single_journal_entry()
                else:
                    je = self.make_payment_journal_entry()

            if je:
                je.insert()
                je.submit()

                self.payment_journal_entry = je.name
                self.approval_comment = None
            
        elif self.workflow_state == "Cancelled":
            # cancel related journal entries
            self.before_cancel()
            if self.docstatus != 2:
                self.docstatus = 2

    def on_change(self): # update
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
            workflow_state = "Quotations Required"
            if self.workflow_state:
                workflow_state = self.workflow_state
            if len(self.approval_history) < 1:
                if self.user_has_role(user, ["Accounts User", "Accounts Manager"]):
                    workflow_state = "Submitted to Accounts"
                        
            self.append("approval_history", {
                "approver": user.name,
                "full_name": user.full_name,
                "approval_status": workflow_state,
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
        # add request_items up and set the total field
        # add default project and cost center to expense items

        total = 0
        count = 0
        expense_items = []

        
        for detail in self.request_items:
            total += float(detail.amount)        
            count += 1
            
            if not detail.project and self.project_name:
                detail.project = self.project_name

            if not detail.activity and self.activity:
                detail.activity = self.activity
            
            if not detail.cost_center and self.cost_center:
                detail.cost_center = self.cost_center

            expense_items.append(detail)

        self.request_items = expense_items

        if self.total != total:
            self.total = total
        if self.total_qty != count:
            self.total_qty = count

    def make_payment_journal_entry_old(self, settings, user):
        # Preparing the JE: convert self details into je account details
        accounts = []

        for detail in self.request_items:            

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

        for detail in self.request_items:            

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
        for detail in self.request_items:
            accounts.append({
                'debit_in_account_currency': float(detail.amount),
                'user_remark': str(detail.description),
                'account': detail.expense_account,
                'project': detail.project,
                'cost_center': detail.cost_center
            })
            
        account_entries = {}

        # Add payable account details
        for detail in self.request_items:
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

    # def make_journal_entry(self, settings, user):
    #     je = []

    #     if self.party_type == "Employee":
    #         if self.payment_date:
    #             je = self.make_employee_advance_je(settings, user)
    #         else:
    #             # check if complete amount is used up
    #             je = self.make_employee_expense_je(settings, user)
    #     else:
    #         if settings.skip_payable_journal_entry == 1:
    #             je = self.make_single_journal_entry(settings, user)
    #         else:
    #             # Determine the type of journal entry to create
    #             if not self.payment_date: # and self.docstatus == 0: 
    #                 # make sure to validate payment reference and date correctly on the form
    #                 je = self.make_payable_journal_entry(settings, user)
    #             elif self.payment_date:
    #                 je = self.make_payment_journal_entry(settings, user)
    #         # frappe.errprint(je.as_dict())
    #         # return	
        
    #     je.insert()
    #     return je.submit()

    def get_employee_account(self, employee: str) -> str:
        """Retrieve or create an account for the specified employee.

        Checks if an account exists for the employee under "Employee Accounts".
        If not, creates a new account under "Current Assets".

        Args:
            employee (str): Employee's name.

        Returns:
            str: Employee's account name.

        Raises:
            frappe.exceptions.ValidationError: If account creation fails.

        Side Effects:
            - May create "Employee Accounts" under "Current Assets".
            - May create a new employee account.
            - Displays account creation messages.

        Example:
            account_name = self.get_employee_account("John Doe")
        """

        employee_account = frappe.get_all('Account', filters={'parent_account': ['like', '%Employee Accounts%'], 'account_name': ['like', f'%{employee}']}, limit=1)

        if employee_account:
            employee_account = employee_account[0].name
        else:
            parent_account_number = "1125"
            parent = frappe.get_all('Account', filters={'account_name': ['like', '%Employee Accounts%'], 'parent_account': ['like', '%Current Assets%']}, limit=1)

            if not parent:
                root_account = frappe.get_all('Account', filters={'account_name': ['like', '%Current Assets%']}, limit=1)
                frappe.errprint(f"root account {root_account}")

                parent = frappe.new_doc("Account")

                parent.account_name = "Employee Accounts"
                parent.account_number = parent_account_number
                parent.parent_account = root_account[0].name
                parent.is_group = 1
                parent.root_type = "Asset"
                parent.report_type = "Balance Sheet"
                parent.account_type = "Cash"
                parent.company = self.company
                parent.insert(ignore_permissions=True)

                frappe.msgprint(f"New account group: {frappe.bold(parent.name)}", indicator='blue', alert=True)

                parent = parent.name
            else:
                parent = parent[0].name            

            employee_accounts = frappe.get_all('Account', filters={'parent_account': ['like', f'%{parent} -']}, limit=0)            
            new_account_number = int(parent_account_number) + len(employee_accounts) + 1

            account = frappe.new_doc("Account")            
            account.account_type = "Cash"
            account.root_type = "Asset"
            account.report_type = "Balance Sheet"
            account.account_name = employee
            account.account_number = new_account_number
            account.parent_account = parent
            account.insert(ignore_permissions=True)
            
            employee_account = account.name
            frappe.msgprint(f"Created employee account {frappe.bold(employee_account)}", indicator='blue', alert=True)

        return employee_account
    

    def make_employee_advance_je(self):
        """
        Create a Journal Entry for an employee advance.

        This method prepares a journal entry for an advance payment to an employee.
        It validates the mode of payment and ensures that a payment reference and date
        are provided for non-cash payments. It retrieves or creates the necessary accounts
        and constructs the journal entry data.

        Returns:
            frappe.Document: A Journal Entry document ready for insertion and submission.

        Raises:
            frappe.exceptions.ValidationError: If the mode of payment lacks a linked account
            or if required payment reference details are missing.

        Side Effects:
            - May throw an error if validation fails.
            - Constructs a journal entry document.

        Example:
            je = self.make_employee_advance_je()
            je.insert()
            je.submit()
        """
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

        employee_account = self.get_employee_account(self.party)
        accounts = [
            {
                'debit_in_account_currency': float(self.total) * self.conversion_rate,
                'user_remark': str(self.remarks or ""),
                'account': employee_account,
                'cost_center': self.cost_center,
                'exchange_rate': self.conversion_rate,
                'party_type': self.party_type,
                'party': self.party,
                'project': self.project_name
            },
            {
                'credit_in_account_currency': float(self.total) * self.conversion_rate,
                'user_remark': str(self.remarks or ""),
                'exchange_rate': self.conversion_rate,
                'account': pay_account,
                'cost_center': self.cost_center
            }
        ]

        # Finally, add the payment account detail
        if self.mode_of_payment != "Cash" and (not self.reference or not self.payment_date):
            frappe.throw(
                title="Enter Payment Reference",
                msg="Payment Reference and Date are Required for all non-cash payments."
            )

        # add journal entry data
        je_data = {
            'title': self.name + ' - Advance',
            'doctype': 'Journal Entry',
            'voucher_type': 'Journal Entry',
            'posting_date': self.payment_date,
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
    
    def make_employee_expense_je(self):
        """
        Create a Journal Entry for employee expenses.

        This method prepares a journal entry for expenses incurred by an employee.
        It validates that the total expenditure and deposit amount match the requisitioned amount.
        It retrieves or creates the necessary accounts and constructs the journal entry data.

        Returns:
            Object: A Journal Entry document ready for insertion and submission.

        Raises:
            frappe.exceptions.ValidationError: If the total expenditure and deposit amount
            do not match the requisitioned amount, or if the mode of payment lacks a linked account.

        Side Effects:
            - May throw an error if validation fails.
            - Constructs a journal entry document.

        Example:
            je = self.make_employee_expense_je()
            je.insert()
            je.submit()
        """

        # validations
        if (self.total_expenditure + self.deposit_amount) != self.total:
            if self.total > (self.total_expenditure + self.deposit_amount):
                frappe.throw(
                    title="Incomplete Expenditure", 
                    msg=f"""Total expenditure + Deposit amount ({frappe.bold(str(self.total_expenditure + self.deposit_amount) + self.currency)}) 
                        cannot be less than the requisitioned amount ({frappe.bold(str(self.total) + self.currency)}). 
                        You can deposit the remaining amount if you spent less."""
                )
            
            if self.total < (self.total_expenditure + self.deposit_amount):
                frappe.throw(
                    title="Overspend",
                    msg="Total Expenditure (and Deposited Amount) cannot exceed the requisitioned amount."
                )
        
        pay_account = frappe.db.get_value('Mode of Payment Account', {
                'parent': self.mode_of_payment, 
                'company': self.company
            },
            'default_account')

        if not pay_account or pay_account == "":
            frappe.throw(
                title="Account Required in Mode of Payment",
                msg="The selected Mode of Payment has no linked account."
            )

        employee_account = self.get_employee_account(self.party)

        # add employee account detail from which the expense is incurred
        accounts = [
            {
                'credit_in_account_currency': float(self.total) * self.conversion_rate,
                'exchange_rate': self.conversion_rate,                
                'account': employee_account,
                'project': self.project_name,
                'cost_center': self.cost_center,
                'party_type': self.party_type,
                'party': self.party
            }
        ]

        # add expense details
        for detail in self.expense_items:
            accounts.append({
                'debit_in_account_currency': float(detail.amount) * self.conversion_rate,
                'exchange_rate': self.conversion_rate,
                'user_remark': str(detail.description),
                'account': detail.expense_account,
                'project': detail.project,
                'cost_center': detail.cost_center
            })
        
        # add deposit of unspent amount
        if self.deposit_amount > 0:
            accounts.append({
                'debit_in_account_currency': float(self.deposit_amount) * self.conversion_rate,
                'user_remark': "Deposit of unspent amount",
                'exchange_rate': self.conversion_rate,
                'account': pay_account,
                'cost_center': self.cost_center,
                'party': self.party,
                'party_type': self.party_type,
                'project': self.project_name
            })

        # Finally, add the payment account detail
        if self.mode_of_payment != "Cash" and (not self.reference or not self.payment_date):
            frappe.throw(
                title="Enter Payment Reference",
                msg="Payment Reference and Date are Required for all non-cash payments."
            )

        # add journal entry data
        je_data = {
            'title': self.name + ' - Advance',
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
    
    def make_payable_journal_entry(self, settings, user):
        # Preparing the JE for payable entry
        account_entries = {}

        # Group expense details by account key
        for detail in self.request_items:
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
        for detail in self.request_items:
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

        # Group request_items by account
        
        for detail in self.request_items:
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

@frappe.whitelist()
def make_employee_expense_tracker(source_name, target_doc=None):
    def set_missing_values(source, target):
        target.run_method("set_missing_values")

    def update_item(source, target, source_parent):
        target.amount = source.amount
        target.expense_account = source.expense_account
        target.expense_payable_account = source.expense_payable_account

    doc = get_mapped_doc(
        "Payment Requisition",
        source_name,
        {
            "Payment Requisition": {
                "doctype": "Employee Expense Tracker",
                "field_map": {
                    "name": "payment_requisition",
                    "party": "employee",
                    "company": "company",
                    "date": "date",
                    "currency": "currency",
                    "activity": "activity",
                    "project_name": "project",
                    "cost_center": "cost_center"
                },
                "field_no_map": [
                    "approval_history"
                ]
            },
            "Expense Entry Item": {
                "doctype": "Expense Entry Item",
                "field_map": {
                    "description": "description",
                    "amount": "amount",
                    "expense_account": "expense_account",
                    "expense_payable_account": "expense_payable_account",
                    "project": "project",
                    "activity": "activity",
                    "cost_center": "cost_center",
                },
                "postprocess": update_item,
            }
        },
        target_doc,
        # set_missing_values
    )

    return doc

# Add this method to the PaymentRequisition class
@frappe.whitelist()
def create_employee_expense_tracker(self):
    return make_employee_expense_tracker(self.name)

@frappe.whitelist()
def make_payment_requisition(source_name, target_doc=None, args=None):
    def set_missing_values(source, target):
        if len(target.get("request_items")) == 0:
            frappe.throw(_("All request items have already been added"))

        target.party_type = "Employee"
        target.employee = source.party
        target.date = source.date

        target.run_method("set_missing_values")
        target.run_method("calculate_totals")

    def update_item(source_doc, target_doc, source_parent):
        target_doc.amount = source_doc.amount
        target_doc.description = source_doc.description

    doclist = get_mapped_doc(
        "Payment Requisition",
        source_name,
        {
            "Payment Requisition": {
                "doctype": "Employee Expense Tracker",
                "field_map": {
                    "name": "payment_requisition",
                    "employee": "party",
                    "company": "company",
                    "date": "date",
                    "currency": "currency",
                    "activity": "activity",
                    "project": "project_name",
                    "cost_center": "cost_center"
                },
                "validation": {
                    "docstatus": ["=", 1],
                },
            },
            # "Expense Entry Item": {
            #     "doctype": "Expense Entry Item",
            #     "field_map": {
            #         "name": "expense_entry_item",
            #         "amount": "amount",
            #         "description": "description",
            #         "cost_center": "cost_center",
            #     },
            #     "postprocess": update_item,
            # },
        },
        target_doc,
        set_missing_values,
    )

    return doclist


