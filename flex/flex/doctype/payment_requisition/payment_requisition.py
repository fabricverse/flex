# Copyright (c) 2024, Fabric and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class PaymentRequisition(Document):        
    def autoname(self):
        self.name = self.generate_custom_name()
    
    def after_insert(self):
        self.db_set("allow_incomplete_quotations", 0)
        self.notify_update()
    
    @frappe.whitelist()
    def apply_workflow(self, user):
        if len(self.request_items) < 1:
            return
        settings = frappe.get_single("Payment Requisition Settings")

        self.calculate_totals()

        if self.workflow_state == "Accounts Verification":
            self.validate_totals()
        
        if self.workflow_state == "Capture Expenses" and not self.payable_journal_entry:
            je = None
            # Create payable journal entry
            if self.party_type == "Employee":
                je = self.make_employee_advance_je()
            else:
                if settings.skip_payable_journal_entry == 0:
                    je = self.make_supplier_payable_je(settings, user)
            
            if je:
                self.payable_journal_entry = je.name
                self.approval_comment = None
                
        elif self.workflow_state == "Closed":
            je = None
            if self.party_type == "Employee":
                je = self.make_employee_expense_je()
            else:
                if not self.reference and self.mode_of_payment != "Cash":
                    frappe.throw("{} is required for non-cash payments.".format(frappe.bold("Payment Reference")))

                if settings.skip_payable_journal_entry == 1:
                    je = self.make_single_supplier_je(settings, user)
                else:
                    je = self.make_supplier_payment_je(settings, user)

            if je:
                self.expense_journal_entry = je.name
                self.approval_comment = None
            
        elif self.workflow_state == "Cancelled":
            # cancel related journal entries
            self.before_cancel()

                
    def validate_totals(self):
        if not self.total_expenditure or not self.deposit_amount or not self.total:
            self.calculate_totals()

        if (flt(self.total_expenditure) + flt(self.deposit_amount)) != flt(self.total):
            if (flt(self.total_expenditure) + flt(self.deposit_amount)) == 0:
                frappe.throw(
                    title="Expenses Required",
                    msg="Enter expenses equal to the total requisitioned amount or deposit the unspent amount."
                )
            if flt(self.total) > (flt(self.total_expenditure) + flt(self.deposit_amount)):
                frappe.throw(
                    title="Incomplete Expenditure", 
                        msg=f"""Total expenditure + Deposit amount ({frappe.bold(str(self.total_expenditure + self.deposit_amount) + self.currency)}) 
                        cannot be less than the requisitioned amount ({frappe.bold(str(self.total) + self.currency)}). 
                        You can deposit the remaining amount if you spent less."""
                )
            
            if flt(self.total) < (flt(self.total_expenditure) + flt(self.deposit_amount)):
                frappe.throw(
                    title="Overspend",
                    msg="Total Expenditure (and Deposited Amount) cannot exceed the requisitioned amount."
                )
        return True
    def on_change(self): # update
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
        # go straight to attach docs workflow state, otherwise go to Pending Internal Check


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

        if self.workflow_state not in ["Payment Due", "Closed"]:
            self.approval_comment = None

    def validate(self):		
        user = frappe.get_doc("User", frappe.session.user)
        self.apply_workflow(user)
        
        if self.docstatus == 0 and self.workflow_state in ["Submitted to Accounts", "Quotations Required", "Revision Requested", "Employee Revision Required"]:
            if not self.raised_by:
                owner = frappe.get_doc("User", self.owner)
                self.raised_by = owner.full_name

            self.submitted_by = "Pending"
            self.checked_by = "Pending"
            self.initial_approver = "Pending"
            self.final_approver = "Pending"

        if self.workflow_state in ["Quotations Required", "Submitted to Accounts", "Ready for Submission"]:

            if self.user_has_role(user, ["Accounts User", "Accounts Manager"]) and self.submitted_by == "Pending":
                self.submitted_by = user.full_name
                

        if self.workflow_state in ["Ready for Submission", "Pending Internal Check",]:
            if not self.submitted_by or self.submitted_by != user.full_name:
                self.submitted_by = user.full_name

        if self.workflow_state == "Pending First Approval":
            self.checked_by = user.full_name

        if self.workflow_state == "Pending Final Approval":
            self.initial_approver = user.full_name
            
        if self.workflow_state == "Payment Due":
            self.final_approver = user.full_name

        self.workflow_log(user)


    def calculate_totals(self):
        # add request_items up and set the total field
        # add default project and cost center to expense items

        total = 0
        total_base = 0
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
        if self.total_base != (total * self.conversion_rate):
            self.total_base = flt(total * self.conversion_rate)
        if self.total_qty != count:
            self.total_qty = count

        # Calculate total expenditure
        total_expenditure = 0
        if self.expense_items:
            for item in self.expense_items:
                total_expenditure += float(item.amount)

        if self.total_expenditure != total_expenditure:
            self.total_expenditure = total_expenditure
        if self.total_expenditure_based != (total_expenditure * self.conversion_rate):
            self.total_expenditure_based = flt(total_expenditure * self.conversion_rate)

        # Update deposit amount if it exceeds available balance
        if flt(self.total) != flt(self.total_expenditure) + flt(self.deposit_amount):
            if flt(self.deposit_amount) > 0:
                updated_deposit_amount = flt(self.total) - flt(self.total_expenditure)
                self.deposit_amount = updated_deposit_amount
                frappe.msgprint(
                    "Deposit Amount Updated", 
                    indicator="blue",
                    alert=True
                )



    def make_single_supplier_je(self, settings, user):
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

        je.insert()
        je.submit()

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

        # if self.workflow_state != "Cancelled":
        self.workflow_state = "Cancelled"        
        self.docstatus = 1
    
        frappe.db.commit()


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

            employee_accounts = frappe.get_all('Account', filters={'parent_account': ['like', f'%{parent}']}, limit=0)            
            new_account_number = int(parent_account_number) + (len(employee_accounts) + 1)

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
        """
        if not self.payment_date:
            frappe.throw(
                title="Enter Payment Date",
                msg="Payment Date is Required for all payments."
            )
        if self.mode_of_payment != "Cash" and not self.reference:
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

        employee_account = self.get_employee_account(self.party)
        accounts = [
            {
                'debit_in_account_currency': float(self.total) * (self.conversion_rate or 1),
                'user_remark': str(self.remarks or ""),
                'account': employee_account,
                'cost_center': self.cost_center,
                'exchange_rate': self.conversion_rate,
                'party_type': self.party_type,
                'party': self.party,
                'project': self.project_name
            },
            {
                'credit_in_account_currency': float(self.total) * (self.conversion_rate or 1),
                'user_remark': str(self.remarks or ""),
                'exchange_rate': self.conversion_rate,
                'account': pay_account,
                'cost_center': self.cost_center
            }
        ]

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

        je.insert()
        je.submit()

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
        """

        # validations
        self.validate_totals()
        
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
                'credit_in_account_currency': float(self.total) * (self.conversion_rate or 1),
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
            reference = " reference: " + detail.reference if detail.reference else ""
            accounts.append({
                'debit_in_account_currency': float(detail.amount) * (self.conversion_rate or 1),
                'exchange_rate': self.conversion_rate,
                'user_remark': str((detail.description + reference) or ""),
                'account': detail.expense_account,
                'project': detail.project,
                'cost_center': detail.cost_center,
                'party_type': "Supplier" if detail.supplier else None,
                'party': detail.supplier if detail.supplier else None
            })
        
        # add deposit of unspent amount
        if flt(self.deposit_amount) > 0:
            accounts.append({
                'debit_in_account_currency': float(self.deposit_amount) * (self.conversion_rate or 1),
                'user_remark': "Deposit of unspent amount reference: " + self.deposit_reference,
                'exchange_rate': self.conversion_rate,
                'account': pay_account,
                'cost_center': self.cost_center,
                'party': self.party,
                'party_type': self.party_type,
                'project': self.project_name
            })

        # Finally, add the payment account detail

        if not self.payment_date:
            frappe.throw(
                title="Enter Payment Date",
                msg="Payment Date is Required for all payments."
            )
        if self.mode_of_payment != "Cash" and not self.reference:
            frappe.throw(
                title="Enter Payment Reference",
                msg="Payment Reference and Date are Required for all non-cash payments."
            )

        # add journal entry data
        je_data = {
            'title': self.name + ' - Expense',
            'doctype': 'Journal Entry',
            'voucher_type': 'Journal Entry',
            'posting_date': self.modified,
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

        je.insert()
        je.submit()

        return je
    
    def make_supplier_payable_je(self, settings, user):
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
                # increment existing entry amount amount
                account_entries[account_key]['debit_in_account_currency'] += float(detail.amount) * (self.conversion_rate or 1)
            else:
                # add entry
                account_entries[account_key] = {
                    'debit_in_account_currency': float(detail.amount) * (self.conversion_rate or 1),
                    'user_remark': str(detail.description),
                    'account': detail.expense_account,
                    'project': detail.project,
                    'cost_center': detail.cost_center,
                    'party_type': self.party_type,
                    'party': self.party
                }

        # Group payable account details
        for detail in self.request_items:

            payable_account = detail.expense_payable_account
            if not payable_account:
                payable_account = frappe.db.get_value('Expense Item', detail.expense_item, 'default_payable_account')
                
                if not payable_account:
                    payable_account = settings.default_payable_account

                    if not payable_account:
                        frappe.throw(f"Please set a Default Expense Payable Account in <a href='{settings.get_url()}'>Payment Requisition Settings.</a>")
            account_key = (
                payable_account,
                detail.project,
                detail.cost_center,
                self.party_type,
                self.party,
            )
            
            if account_key in account_entries:
                if 'credit_in_account_currency' in account_entries[account_key]:
                    account_entries[account_key]['credit_in_account_currency'] += float(detail.amount) * (self.conversion_rate or 1)
                else:
                    account_entries[account_key]['credit_in_account_currency'] = float(detail.amount) * (self.conversion_rate or 1)
                    account_entries[account_key]['user_remark'] = 'Amount payable to supplier'
                    account_entries[account_key]['account'] = payable_account
            else:

                account_entries[account_key] = {
                    'credit_in_account_currency': float(detail.amount) * (self.conversion_rate or 1),
                    'user_remark': 'Amount payable to supplier',
                    'account': payable_account,
                    'project': detail.project,
                    'cost_center': detail.cost_center,
                    'party_type': self.party_type,
                    'party': self.party
                }

        # Prepare accounts list
        
        accounts = list(account_entries.values())
        print(accounts)

        # Create the journal entry document
        je = frappe.get_doc({
            'title': self.name + ' - Payable',
            'doctype': 'Journal Entry',
            'voucher_type': 'Journal Entry',
            'posting_date': self.date,
            'company': self.company,
            'accounts': accounts,
            'user_remark': self.remarks,
            # 'mode_of_payment': self.mode_of_payment,
            'pay_to_recd_from': self.party,
            'bill_no': self.name
        })

        je.insert()
        je.submit()

        return je


    def make_supplier_payment_je(self, settings, user):
        # Preparing the JE: convert self details into JE account details
        account_entries = {}

        # Group request_items by account
        for detail in self.expense_items:            
            expense_payable_account = detail.expense_payable_account
            if not expense_payable_account:
                expense_payable_account = settings.default_payable_account

            account_key = (
                detail.expense_account,
                detail.project,
                detail.cost_center
            )
            
            if account_key in account_entries:
                account_entries[account_key]['debit_in_account_currency'] += flt(detail.amount * (self.conversion_rate or 1), 3)
                
                account_entries[account_key]['account'] = expense_payable_account
            else:
                account_entries[account_key] = {
                    'debit_in_account_currency': flt(detail.amount * (self.conversion_rate or 1), 3),
                    'user_remark': str(detail.description),
                    'account': expense_payable_account,
                    'project': detail.project,
                    'cost_center': detail.cost_center,
                    'party_type': self.party_type,
                    'party': self.party
                }

        # Finally, add the payment account detail

        if not self.payment_date:
            frappe.throw(
                title="Enter Payment Date",
                msg="Payment Date is Required for all payments."
            )
        if self.mode_of_payment != "Cash" and not self.reference:
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

        # add deposit of unspent amount
        if flt(self.deposit_amount) > 0:
            accounts.append({
                'debit_in_account_currency': flt(self.deposit_amount) * (self.conversion_rate or 1),
                'user_remark': "Deposit of unspent amount reference: " + self.deposit_reference,
                'exchange_rate': self.conversion_rate,
                'account': pay_account,
                'cost_center': self.cost_center,
                'party': self.party,
                'party_type': self.party_type,
                'project': self.project_name
            })
        
        # Add the payment entry
        accounts.append({
            'credit_in_account_currency': flt(self.total * (self.conversion_rate or 1), 3),
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
        je.insert()
        je.submit()

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
