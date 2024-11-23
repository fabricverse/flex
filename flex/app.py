import frappe
from frappe import _
from frappe.model.document import Document


def create_project_cost_center(doc, method):
    company = frappe.get_doc("Company", doc.company)
    projects_cc = f"Projects - {company.abbr}"

    if not frappe.db.exists("Cost Center", projects_cc):

        cc = frappe.new_doc("Cost Center")
        cc.cost_center_name = "Projects"
        cc.parent_cost_center = f"{company.name} - {company.abbr}"
        cc.is_group = 1
        cc.company = doc.company
        cc.insert(ignore_permissions=True)

    cc = frappe.new_doc("Cost Center")
    cc.cost_center_name = f"{doc.project_name}"
    cc.parent_cost_center = projects_cc
    cc.is_group = 0
    cc.company = doc.company    
    cc.insert(ignore_permissions=True)

    doc.cost_center = cc.name
    doc.db_update()

@frappe.whitelist()
def requisition_action(name, action):
    doc = frappe.get_doc("Payment Requisition", name)
    doc.requisition_action(action)

@frappe.whitelist()
def save_comment(reference_doctype, reference_name, content, comment_email, comment_by):
    doc = frappe.get_doc(reference_doctype, reference_name)
    doc.add_comment('Comment', text=content)
    doc.query = content
    doc.queried_by = comment_by
    doc.save()
    doc.reload()

    print('queried_by', frappe.get_value(reference_doctype, reference_name, "queried_by"))


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