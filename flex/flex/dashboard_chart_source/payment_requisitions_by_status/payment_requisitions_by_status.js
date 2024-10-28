frappe.dashboards.chart_sources["Payment Requisitions by Status"] = {
	method: "flex.flex.dashboard_chart_source.payment_requisitions_by_status.payment_requisitions_by_status.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		}
	]
};