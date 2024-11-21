import frappe
from frappe import _

def execute(filters=None):
    return get_columns(filters), get_data(filters)

def get_data(filters):
    conditions = ["pr.docstatus = 1"]  # Only submitted documents

    if filters.get('from_date'):
        conditions.append(f"pr.payment_date >= '{filters.get('from_date')}'")
    if filters.get('to_date'):
        conditions.append(f"pr.payment_date <= '{filters.get('to_date')}'")
    
    if filters.get('company'):
        conditions.append(f"pr.company = '{filters.get('company')}'")
    if filters.get('party_type'):
        conditions.append(f"pr.party_type = '{filters.get('party_type')}'")
    if filters.get('party'):
        conditions.append(f"pr.party = '{filters.get('party')}'")
    if filters.get('activity'):
        conditions.append(f"pr.activity = '{filters.get('activity')}'")
    if filters.get('project'):
        conditions.append(f"pr.project_name = '{filters.get('project')}'")
    if filters.get('cost_center'):
        conditions.append(f"pr.cost_center = '{filters.get('cost_center')}'")
    if filters.get('workflow_state'):
        if filters.get('workflow_state') == "Closed & Unsettled":
            condition = "pr.workflow_state IN ('Closed', 'Payment Due', 'Capture Expenses', 'Expense Revision', 'Accounts Approval')"
        else:
            condition = f"pr.workflow_state = '{filters.get('workflow_state')}'"
        conditions.append(condition)
        
    conditions_sql = " AND ".join(conditions)
    if conditions_sql:
        conditions_sql = "WHERE " + conditions_sql

    group_by_field = filters.get('group_by')
    group_by_sql = ""
    select_fields = [
        "pr.name as payment_requisition",
        "pr.payment_date as date",
        "pr.party_type as party_type", 
        "pr.party as party", 
        "act.subject as activity", 
        "pr.project_name as project", 
        "pr.cost_center as cost_center",
        "CASE WHEN pr.currency != comp.default_currency THEN pr.total * pr.conversion_rate ELSE pr.total END as requested_amount",
        "CASE WHEN pr.currency != comp.default_currency THEN pr.total_expenditure * pr.conversion_rate ELSE pr.total_expenditure END as spent_amount",
        "CASE WHEN pr.currency != comp.default_currency THEN pr.deposit_amount * pr.conversion_rate ELSE pr.deposit_amount END as deposit_amount",
        "CASE WHEN pr.currency != comp.default_currency THEN (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) * pr.conversion_rate ELSE (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) END as balance"
    ]

    if group_by_field:
        if group_by_field == "Party Type":
            group_by_sql = "GROUP BY pr.party_type"
            select_fields = [
                "pr.party_type as party_type",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total * pr.conversion_rate ELSE pr.total END) as requested_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total_expenditure * pr.conversion_rate ELSE pr.total_expenditure END) as spent_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.deposit_amount * pr.conversion_rate ELSE pr.deposit_amount END) as deposit_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) * pr.conversion_rate ELSE (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) END) as balance"
            ]
        elif group_by_field == "Party":
            group_by_sql = "GROUP BY pr.party"
            select_fields = [
                "pr.party_type as party_type", 
                "pr.party as party",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total * pr.conversion_rate ELSE pr.total END) as requested_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total_expenditure * pr.conversion_rate ELSE pr.total_expenditure END) as spent_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.deposit_amount * pr.conversion_rate ELSE pr.deposit_amount END) as deposit_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) * pr.conversion_rate ELSE (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) END) as balance"
            ]
        elif group_by_field == "Project":
            group_by_sql = "GROUP BY pr.project_name"
            select_fields = [
                "pr.project_name as project",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total * pr.conversion_rate ELSE pr.total END) as requested_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total_expenditure * pr.conversion_rate ELSE pr.total_expenditure END) as spent_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.deposit_amount * pr.conversion_rate ELSE pr.deposit_amount END) as deposit_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) * pr.conversion_rate ELSE (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) END) as balance"
            ]
        elif group_by_field == "Activity":
            group_by_sql = "GROUP BY pr.activity"
            select_fields = [
                "act.subject as activity",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total * pr.conversion_rate ELSE pr.total END) as requested_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total_expenditure * pr.conversion_rate ELSE pr.total_expenditure END) as spent_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.deposit_amount * pr.conversion_rate ELSE pr.deposit_amount END) as deposit_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) * pr.conversion_rate ELSE (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) END) as balance"
            ]
        elif group_by_field == "Cost Center":
            group_by_sql = "GROUP BY pr.cost_center"
            select_fields = [
                "pr.cost_center as cost_center",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total * pr.conversion_rate ELSE pr.total END) as requested_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.total_expenditure * pr.conversion_rate ELSE pr.total_expenditure END) as spent_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN pr.deposit_amount * pr.conversion_rate ELSE pr.deposit_amount END) as deposit_amount",
                "SUM(CASE WHEN pr.currency != comp.default_currency THEN (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) * pr.conversion_rate ELSE (pr.total - IFNULL(pr.total_expenditure + pr.deposit_amount, 0)) END) as balance"
            ]
    
    select_fields_sql = ", ".join(select_fields)

    query = f"""SELECT {select_fields_sql}
                FROM `tabPayment Requisition` as pr
                LEFT JOIN `tabTask` AS act 
                ON pr.activity = act.name
                LEFT JOIN `tabCompany` AS comp
                ON pr.company = comp.name
                {conditions_sql}
                {group_by_sql}
                ORDER BY pr.payment_date DESC
            """
    
    data = frappe.db.sql(query, as_dict=1)
    return data

def get_columns(filters):
    company = filters.get('company')
    currency = frappe.get_cached_value('Company', company, 'default_currency') if company else frappe.defaults.get_global_default('currency')
    
    group_by_field = filters.get('group_by')
    if not group_by_field:
        return [
            {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
            {"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Link", "options": "DocType", "width": 100},
            {"label": _("Party"), "fieldname": "party", "fieldtype": "Dynamic Link", "options": "party_type", "width": 180},
            {"label": _("Requested ({0})").format(currency), "fieldname": "requested_amount", "fieldtype": "Float", "width": 180},
            {"label": _("Spent ({0})").format(currency), "fieldname": "spent_amount", "fieldtype": "Float", "width": 180},
            {"label": _("Deposited ({0})").format(currency), "fieldname": "deposit_amount", "fieldtype": "Float", "width": 180},
            {"label": _("Balance ({0})").format(currency), "fieldname": "balance", "fieldtype": "Float", "width": 180},
            {"label": _("Requisition"), "fieldname": "payment_requisition", "fieldtype": "Link", "options": "Payment Requisition", "width": 200},
            {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 200},
            {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
            {"label": _("Activity"), "fieldname": "activity", "fieldtype": "Data", "width": 200}
        ]
    
    if group_by_field:
        print('group_by_field', group_by_field)
        if group_by_field == "Party Type":
            columns = [
                {"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Link", "options": "DocType", "width": 200},
                {"label": _("Requested Amount ({0})").format(currency), "fieldname": "requested_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Spent Amount ({0})").format(currency), "fieldname": "spent_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Deposit Amount ({0})").format(currency), "fieldname": "deposit_amount", "fieldtype": "Float", "width": 130},
                {"label": _("Balance ({0})").format(currency), "fieldname": "balance", "fieldtype": "Float", "width": 200}
            ]
        elif group_by_field == "Party":
            columns = [
                {"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Link", "options": "DocType", "width": 150},
                {"label": _("Party"), "fieldname": "party", "fieldtype": "Dynamic Link", "options": "party_type", "width": 200},
                {"label": _("Requested Amount ({0})").format(currency), "fieldname": "requested_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Spent Amount ({0})").format(currency), "fieldname": "spent_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Deposit Amount ({0})").format(currency), "fieldname": "deposit_amount", "fieldtype": "Float", "width": 130},
                {"label": _("Balance ({0})").format(currency), "fieldname": "balance", "fieldtype": "Float", "width": 200}
            ]
        elif group_by_field == "Project":
            columns = [
                {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 300},
                {"label": _("Requested Amount ({0})").format(currency), "fieldname": "requested_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Spent Amount ({0})").format(currency), "fieldname": "spent_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Deposit Amount ({0})").format(currency), "fieldname": "deposit_amount", "fieldtype": "Float", "width": 130},
                {"label": _("Balance ({0})").format(currency), "fieldname": "balance", "fieldtype": "Float", "width": 200}
            ]
        elif group_by_field == "Activity":
            columns = [
                {"label": _("Activity"), "fieldname": "activity", "fieldtype": "Data", "width": 300},
                {"label": _("Requested Amount ({0})").format(currency), "fieldname": "requested_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Spent Amount ({0})").format(currency), "fieldname": "spent_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Deposit Amount ({0})").format(currency), "fieldname": "deposit_amount", "fieldtype": "Float", "width": 130},
                {"label": _("Balance ({0})").format(currency), "fieldname": "balance", "fieldtype": "Float", "width": 200}
            ]
        elif group_by_field == "Cost Center":
            columns = [
                {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 300},
                {"label": _("Requested Amount ({0})").format(currency), "fieldname": "requested_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Spent Amount ({0})").format(currency), "fieldname": "spent_amount", "fieldtype": "Float", "width": 200},
                {"label": _("Deposit Amount ({0})").format(currency), "fieldname": "deposit_amount", "fieldtype": "Float", "width": 130},
                {"label": _("Balance ({0})").format(currency), "fieldname": "balance", "fieldtype": "Float", "width": 200}
            ]

    return columns


@frappe.whitelist()
def has_multiple_companies():
    company_count = frappe.db.count('Company')
    more_than_one_company_exists = company_count > 1
    return more_than_one_company_exists

