let more_than_one_company_exists = false;

frappe.call({
    method: "flex.flex.report.party_balance_report.party_balance_report.has_multiple_companies",
    callback: function(r) {
        more_than_one_company_exists = String(r.message);
        console.log("more_than_one_company_exists", more_than_one_company_exists);

        frappe.query_reports["Party Balance Report"] = {
            "filters": [
                {
                    "fieldname": "company",
                    "label": __("Company"),
                    "fieldtype": "Link",
                    "options": "Company",
                    "default": frappe.defaults.get_user_default("Company"),
                    "depends_on": "eval:" + more_than_one_company_exists,
                    "reqd": 1,
                    "width": "100"
                },
                {
                    "fieldname": "from_date",
                    "label": __("From Date"),
                    "fieldtype": "Date",
                    "default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
                    "width": "100"
                },
                {
                    "fieldname": "to_date",
                    "label": __("To Date"),
                    "fieldtype": "Date",
                    "default": frappe.datetime.get_today(),
                    "width": "100"
                },
                {
                    "fieldname": "workflow_state",
                    "label": __("Status"),
                    "fieldtype": "Select",
                    "width": "100",
                    "options": [
                        "Closed",
                        "Closed & Unsettled",
                    ],
                    "default": "Closed"
                },
                {
                    "fieldname": "party_type",
                    "label": __("Party Type"),
                    "fieldtype": "Link",
                    "options": "DocType",
                    "width": "100",
                    "get_query": function() {
                        return {
                            filters: {
                                "name": ["in", ["Supplier", "Employee"]]
                            }
                        };
                    },
                    "on_change": function() {
                        var party_type = frappe.query_report.get_filter_value('party_type');
                        frappe.query_report.set_filter_value('party', "");
                        
                        if (party_type) {
                            frappe.query_report.get_filter('party').df.options = party_type;
                        }
                        frappe.query_report.refresh();
                    }
                },
                {
                    "fieldname": "party",
                    "label": __("Party"),
                    "fieldtype": "Dynamic Link",
                    "width": "200",
                    "get_options": function() {
                        return frappe.query_report.get_filter_value('party_type');
                    },
                    "depends_on": "party_type",
                    "on_change": function() {
                        frappe.query_report.refresh();
                    }
                },
                {
                    "fieldname": "group_by",
                    "label": __("Group By"),
                    "fieldtype": "Select",
                    "width": "100",
                    "options": [
                        "",
                        "Party Type",
                        "Party",
                        "Project",
                        "Activity",
                        "Cost Center"
                    ],
                    "default": ""
                },
                {
                    "fieldname": "project",
                    "label": __("Project"),
                    "fieldtype": "Link",
                    "options": "Project",
                    "width": "200"
                },
                {
                    "fieldname": "activity",
                    "label": __("Activity"),
                    "fieldtype": "Link",
                    "options": "Task",
                    "width": "200"
                },
                {
                    "fieldname": "cost_center",
                    "label": __("Cost Center"),
                    "fieldtype": "Link",
                    "options": "Cost Center",
                    "width": "120"
                }
            ],

            onload: function(report) {
                report.page.add_inner_button(__("Reset Filters"), function() {
                    // Reset each filter to its default value or empty
                    report.filters.forEach(filter => {
                        report.set_filter_value(filter.fieldname, filter.default || '');
                    });
                });
            },

            // Uncomment and use if needed
            // formatter: function(value, row, column, data, default_formatter) {
            //     value = default_formatter(value, row, column, data);
                
            //     if (column.fieldname === "balance") {
			// 		if (data.balance > 0) {
			// 			value = `<div style="color:red;">${value}</div>`;
			// 		} else if (data.balance == 0) {
			// 			value = `<div style="color:black;">${value}</div>`;
			// 		}
			// 	}
                
            //     return value;
            // },
			formatter: function (value, row, column, data, default_formatter) {
				value = default_formatter(value, row, column, data);
				
				// Ensure data and balance are defined before proceeding
				if (data && column.fieldname === "balance") {
					if (data.balance > 0) {
						value = "<span style='color:red'>" + value + "</span>";
					}
				}
		
				return value;
			},
        };
    }
});
