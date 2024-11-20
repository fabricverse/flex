import frappe
from frappe import _
from frappe.model.document import Document

@frappe.whitelist()
def requisition_action(name, action):
    doc = frappe.get_doc("Payment Requisition", name)
    doc.requisition_action(action)

@frappe.whitelist()
def my_approvals_card_data():
    user = frappe.session.user
    workflow = frappe.get_doc("Workflow", "Payment Requisition")
    transitions = workflow.transitions
    user_roles = frappe.get_roles(user)
    
    # Create a list of states where the user has the required role
    workflow_list = []
    for row in transitions:
        if row.allowed in user_roles:
            workflow_list.append(row.state)

    # remove non-approval states
    # workflow_list = [state for state in workflow_list if state not in ("Quotations Required", "Employee Revision Required", "Capture Expenses", "Revision Requested", "Expense Revision", "Cancelled", "Rejected")]

    my_approval_workflows = []
    if "Executive Director" in user_roles:
        my_approval_workflows.append("Pending Internal Check")
    if "First Approver" in user_roles:
        my_approval_workflows.append("Pending First Approval")
    if "Final Approver" in user_roles:
        my_approval_workflows.append("Pending Final Approval")
    if "Accounts User" in user_roles or "Accounts Manager" in user_roles:
        my_approval_workflows.append("Submitted to Accounts")
        my_approval_workflows.append("Accounts Verification")


    workflow_list = [state for state in workflow_list if state in my_approval_workflows]

    
    # Remove duplicates if any
    user_workflows = set(workflow_list)

    if len(user_workflows) == 0:
        return {
            "value": 0,
            "fieldtype": "Int",
            "route_options": {},
            "route": ["payment-requisition"]
        }
    
    count = frappe.db.count("Payment Requisition", {
        "workflow_state": ["in", user_workflows]
    })

    return {
        "value": count,
        "fieldtype": "Int",
        "route_options": {
            "workflow_state": ["in", workflow_list]
        },
        "route": ["payment-requisition"]
    }

def add_doc_attachments(doc, method):
    if not doc.reference_doctype == "Payment Requisition": return

    status = frappe.get_value("Payment Requisition", doc.reference_doctype, "workflow_state")
    if status == "Capture Expenses": return

    files = frappe.db.get_all('File',{'attached_to_name': doc.reference_name}) #list of attachments linked to ref. doc

    if len(files) > 0:
        s = []
        for file in files:
            s.append('{"fid": "'+ file.name +'"}')  #append to temp field in format: {"fid": "xxxxx"}
    
        out = frappe.utils.comma_sep(s,'{0}, {1}', add_quotes=False)    #implode to "one" row separed by comma
        if len(doc.attachments) == 2:   #if original att is empty => "[]"
            doc.attachments = f'[{out}]'
        else: 
            #else add attachments
            doc.attachments = doc.attachments.replace('}]','}, '+ out + ']' )
        doc.save()

@frappe.whitelist()
def my_requisitions_card_data():
    user_email = frappe.session.user
    

    if user_email != "Administrator": # Check if user is linked to any employee profile
        employee_exists = frappe.db.sql("""
            SELECT 1
            FROM `tabEmployee`
            WHERE user_id = %s
                OR personal_email = %s
                OR company_email = %s
            LIMIT 1
        """, (user_email, user_email, user_email))

        if not employee_exists:
            frappe.msgprint("You are not linked to any employee profile. Ask your administrator to help you with this.", indicator="warning", alert=True)
            # return {
            #     "value": 0,
            #     "fieldtype": "Int",
            #     "route_options": {
            #         "name": ["in", pr_names]
            #     },
            #     "route": ["payment-requisition"]
            # }
    
    pr_names = ['0']
    count = 0
    
    rows = frappe.db.sql(f"""
        SELECT pr.name
        FROM `tabPayment Requisition` as pr
        LEFT JOIN `tabEmployee` AS emp  
        ON pr.party = emp.employee
        WHERE pr.owner = '{user_email}'
        OR (emp.user_id = '{user_email}' OR emp.personal_email = '{user_email}' OR emp.company_email = '{user_email}')
    """)
    if rows:
        pr_names = rows
        count = len(pr_names)

    return {
        "value": count,
        "fieldtype": "Int",
        "route_options": {
            "name": ["in", pr_names]
        },
        "route": ["payment-requisition"]
    }


# @frappe.whitelist()
# def approve(doc, method):
#     # define important variables
#     curr_user = frappe.session.user
#     cache_key = f"approvers_for_{doc.doctype}_{doc.name}"
#     approvers = frappe.cache().get_value(cache_key) or []
#     wrk_state_changed = doc.has_value_changed("workflow_state")


#     if wrk_state_changed and doc.workflow_state != "Open" and doc.workflow_state != "Rejected":
#         approver_record = doc.get("approvers",{
#             "approver": curr_user,
#             "approval_status": ""
#         })
#         if approver_record:
#             # User has already taken an action
#             if approver_record.approval_status == "Approved":
#                 # User is trying to approve again
#                 frappe.throw("User has already approved")
#             else:
#                 # User is changing their mind from rejected to approved
#                 approver_record.approval_status = "Approved"
#         else:
#             # User is approving for the first time
#             approvers.append(curr_user)
#             doc.append("approvers", {
#                 "approver": curr_user,
#                 "approval_status": "Approved"
#             })
#     elif wrk_state_changed and doc.workflow_state == "Rejected":
#         doc.append("approvers",{
#             "approver": curr_user,
#             "approval_status": "Rejected"
#         })

#     frappe.cache().set_value(cache_key, approvers)




# def setup(expense_entry, method):
#     # add expenses up and set the total field
#     # add default project and cost center to expense items

#     total = 0
#     count = 0
#     expense_items = []

    
#     for detail in expense_entry.expenses:
#         total += float(detail.amount)        
#         count += 1
        
#         if not detail.project and expense_entry.default_project:
#             detail.project = expense_entry.default_project
        
#         if not detail.cost_center and expense_entry.default_cost_center:
#             detail.cost_center = expense_entry.default_cost_center

#         expense_items.append(detail)

#     expense_entry.expenses = expense_items

#     expense_entry.total = total
#     expense_entry.quantity = count

#     make_journal_entry(expense_entry)




# def make_journal_entry(expense_entry):

#     if expense_entry.status == "Approved":         

#         # check for duplicates
        
#         if frappe.db.exists({'doctype': 'Journal Entry', 'bill_no': expense_entry.name}):
#             frappe.throw(
#                 title="Error",
#                 msg="Journal Entry {} already exists.".format(expense_entry.name)
#             )


#         # Preparing the JE: convert expense_entry details into je account details

#         accounts = []

#         for detail in expense_entry.expenses:            

#             accounts.append({  
#                 'debit_in_account_currency': float(detail.amount),
#                 'user_remark': str(detail.description),
#                 'account': detail.expense_account,
#                 'project': detail.project,
#                 'cost_center': detail.cost_center
#             })

#         # finally add the payment account detail

#         pay_account = ""

#         if (expense_entry.mode_of_payment != "Cash" and (not 
#             expense_entry.payment_reference or not expense_entry.clearance_date)):
#             frappe.throw(
#                 title="Enter Payment Reference",
#                 msg="Payment Reference and Date are Required for all non-cash payments."
#             )
#         else:
#             expense_entry.clearance_date = ""
#             expense_entry.payment_reference = ""


#         pay_account = frappe.db.get_value('Mode of Payment Account', {'parent' : expense_entry.mode_of_payment, 'company' : expense_entry.company}, 'default_account')
#         if not pay_account or pay_account == "":
#             frappe.throw(
#                 title="Error",
#                 msg="The selected Mode of Payment has no linked account."
#             )

#         accounts.append({  
#             'credit_in_account_currency': float(expense_entry.total),
#             'user_remark': str(detail.description),
#             'account': pay_account,
#             'cost_center': expense_entry.default_cost_center
#         })

#         # create the journal entry
#         je = frappe.get_doc({
#             'title': expense_entry.name,
#             'doctype': 'Journal Entry',
#             'voucher_type': 'Journal Entry',
#             'posting_date': expense_entry.posting_date,
#             'company': expense_entry.company,
#             'accounts': accounts,
#             'user_remark': expense_entry.remarks,
#             'mode_of_payment': expense_entry.mode_of_payment,
#             'cheque_date': expense_entry.clearance_date,
#             'reference_date': expense_entry.clearance_date,
#             'cheque_no': expense_entry.payment_reference,
#             'pay_to_recd_from': expense_entry.payment_to,
#             'bill_no': expense_entry.name
#         })

#         user = frappe.get_doc("User", frappe.session.user)

#         full_name = str(user.first_name) + ' ' + str(user.last_name)
#         expense_entry.db_set('approved_by', full_name)
        

#         je.insert()
#         je.submit()
