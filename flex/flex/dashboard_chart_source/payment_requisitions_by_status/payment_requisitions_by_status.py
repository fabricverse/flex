import frappe
from frappe import _
from frappe.utils.dashboard import cache_source


@frappe.whitelist()
@cache_source
def get(
		chart_name=None,
		chart=None,
		no_cache=None,
		filters=None,
		from_date=None,
		to_date=None,
		timespan=None,
		time_interval=None,
		heatmap_year=None,
	):
	labels, datapoints = [], []
	filters = frappe.parse_json(filters)

	# filter the payment requisitions by status
	pending_approval_statuses = ("Submitted to Accounts", "Awaiting Internal Approval", 
							   "Awaiting Director Approval (1)", "Awaiting Director Approval (2)", 
							   "Accounts Approval", "Payment Due")
	primary_statuses = ("Accounts Approval",) #("Closed",)
	other_statuses = ("Quotations Required", "Employee Revision Required", 
						"Capture Expenses", "Revision Requested", 
						"Expense Revision")
						#"Cancelled", "Rejected", 
	
	company = frappe.defaults.get_user_default("Company")

	# use sql to get the count of payment requisitions by status
	requisitions = frappe.db.sql("""
		SELECT 
			CASE 
				WHEN workflow_state IN %s THEN "Completed"
				WHEN workflow_state IN %s THEN "For Approval"
				WHEN workflow_state IN %s THEN "Rest"
			END as status,
			COUNT(*) as count
		FROM `tabPayment Requisition`
		WHERE (workflow_state IN %s OR workflow_state IN %s OR workflow_state IN %s)
			AND company = %s
		GROUP BY 
			CASE 
				WHEN workflow_state IN %s THEN "Completed"
				WHEN workflow_state IN %s THEN "For Approval"
				WHEN workflow_state IN %s THEN "Rest"
			END
	""", (primary_statuses, pending_approval_statuses, other_statuses,
		  primary_statuses, pending_approval_statuses, other_statuses,
		  company,
		  primary_statuses, pending_approval_statuses, other_statuses), as_dict=1)

	if not requisitions:
		return []

	for requisition in requisitions:
		labels.append(_(requisition.status))
		datapoints.append(requisition.count)

	return {
		"labels": labels,
		"datasets": [{"name": _("Payment Requisitions"), "values": datapoints}],
		"type": "donut",
		"timespan": "Last Year",
	}
