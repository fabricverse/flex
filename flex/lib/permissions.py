import frappe


def get_allowed_requisitions():
    is_approver = approver_check()
    my_requisitions = get_my_requisitions()

    return my_requisitions, is_approver

@frappe.whitelist()
def approver_check():
    user_roles = frappe.get_roles(frappe.session.user)
    is_approver = False
    
    if "Executive Director" in user_roles:
        is_approver = True
    elif "First Approver" in user_roles:
        is_approver = True
    elif "Final Approver" in user_roles:
        is_approver = True
    elif "Accounts User" in user_roles or "Accounts Manager" in user_roles:
        is_approver = True

    return is_approver


@frappe.whitelist()
def get_my_requisitions():
    user_email = frappe.session.user
    pr_names = []

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
            return pr_names
    
    rows = frappe.db.sql(f"""
        SELECT pr.name
        FROM `tabPayment Requisition` as pr
        LEFT JOIN `tabEmployee` AS emp  
        ON pr.party = emp.employee
        WHERE pr.owner = '{user_email}'
        OR (emp.user_id = '{user_email}' OR emp.personal_email = '{user_email}' OR emp.company_email = '{user_email}')
    """, as_list=1)
    if rows:
        pr_names = [row[0] for row in rows]

    return pr_names