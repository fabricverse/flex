// Copyright (c) 2024, Fabric and contributors
// For license information, please see license.txt
// console.log("payment requisition list");

// frappe.listview_settings["Payment Requisition"] = {
// 	// add_fields: ["total"],
//     get_indicator: function (doc) {
//         console.log('doc', doc);
// 		const status_colors = {
// 			"Quotations Required": "grey",
// 			"Submitted to Accounts": "grey",
// 			"Employee Revision Required": "grey",
// 			"Awaiting Internal Approval": "grey",
// 			"Awaiting Director Approval (1)": "grey",
// 			"Awaiting Director Approval (2)": "grey",
// 			"Payment Due": "grey",
// 			"Capture Expenses": "grey",
// 			"Revision Requested": "grey",
// 			"Expense Revision": "grey",
// 			"Accounts Approval": "grey",
// 			"Cancelled": "grey",
// 			"Rejected": "grey",
// 			"Closed": "blue",
//             "Approved": "grey",
//             "Ready for Submission": "grey",
//             "Payment Completed": "blue"
// 		};
// 		return [__(doc.workflow_state), status_colors[doc.workflow_state], "workflow_state,=," + doc.workflow_state];
// 	},
// 	// right_column: "total",
//     refresh(listview, doc) {
//         console.log(listview.data, doc);
//     }
// };

// right_column_title: "Expenses",
	// right_column_value: "total_expenditure",
	// hide_name_column: true,
    // add fields to fetch
    // add_fields: ['reference', 'project_name'],
    // set default filters
	// filters: [
	// 	[
	// 		'workflow_state', 'in', ['Closed', 'Payment Due']
	// 	]  // Add all possible states
    // ],
	
    // hide_name_column: true, // hide the last column which shows the `name`
    // hide_name_filter: true, // hide the default filter field for the name column
    // onload(listview) {
    //     // triggers once before the list is loaded
    // },
    // before_render() {
    //     // triggers before every render of list records
    // },

    // // set this to true to apply indicator function on draft documents too
    // has_indicator_for_draft: false,

    // get_indicator(doc) {
    //     // customize indicator color
    //     if (doc.workflow_state === 'Closed') {
    //         return [__("Closed"), "blue", "workflow_state,=,Closed"];
    //     } else {
    //         return [__("Payment Due"), "red", "workflow_state,=,Payment Due"];
    //     }
    // },
    // primary_action() {
    //     // triggers when the primary action is clicked
	// 	// console.log("primary action");
    // },
    // get_form_link(doc) {
    //     // override the form route for this doc
	// 	// return `/app/flex/payment-requisition/${doc.name}`;
    // },

    // // format how a field value is shown
    // formatters: {
    //     title(val) {
    //         return val.bold();
    //     },
    //     public(val) {
    //         return val ? 'Yes' : 'No';
    //     }
    // },
