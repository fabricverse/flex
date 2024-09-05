// Copyright (c) 2024, Fabric and contributors
// For license information, please see license.txt

function update_totals(frm, cdt, cdn){
	var items = locals[cdt][cdn];
    var total = 0;
    var no_of_expense_items = 0;
    frm.doc.expenses.forEach(
        function(items) { 
            total += items.amount;
            no_of_expense_items +=1;
        });
    frm.set_value("total", total);
    refresh_field("total");
    frm.set_value("no_of_expense_items", no_of_expense_items);
    refresh_field("no_of_expense_items");
}

frappe.ui.form.on('Expense Entry Item', {
	amount: function(frm, cdt, cdn) {
        update_totals(frm, cdt, cdn);
	},
	expenses_remove: function(frm, cdt, cdn){
        update_totals(frm, cdt, cdn);
	},
    expenses_add: function(frm, cdt, cdn){
        var d = locals[cdt][cdn];
        
        if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 

            if (cur_frm.doc.cost_center != "" || typeof cur_frm.doc.cost_center != 'undefined') {
                
                d.cost_center = cur_frm.doc.cost_center; 
                cur_frm.refresh_field("expenses");
            }
        }
	}
	
	
});


function set_queries(frm) {
    frm.set_query("expense_account", 'expenses', () => {
        return {
            filters: [
                ["Account", "root_type", "=", "Expense"],
                ["Account", "is_group", "=", "0"],
                ["Account", "company", "=", frm.doc.company]
            ]
        }
    });
    frm.set_query("cost_center", 'expenses', () => {
        return {
            filters: [
                ["Cost Center", "is_group", "=", "0"],
                ["Cost Center", "company", "=", frm.doc.company]
            ]
        }
    });
    frm.set_query("cost_center", () => {
        return {
            filters: [
                ["Cost Center", "is_group", "=", "0"],
                ["Cost Center", "company", "=", frm.doc.company]
            ]
        }
    });
}

function unset_cost_center(frm) {
    frm.set_value("cost_center", '');
}   

function get_company_currency(company) {
	return erpnext.get_currency(company);
}

function change_form_labels(frm) {
	frm.set_currency_labels(["total"], frm.doc.currency);
}

function change_grid_labels(frm) {
	// update_item_grid_labels(frm);
	if (frm.doc.expenses && frm.doc.expenses.length > 0) {
		frm.set_currency_labels(["amount"], frm.doc.currency, "expenses");
	}
}

function check_currency(frm, company_currency){

	if (frm.doc.currency === company_currency || !frm.doc.currency) {
		frm.set_value("currency", company_currency);
		frm.set_value("conversion_rate", 1);
		cur_frm.set_df_property("conversion_rate", "description", "Default company currency selected");		
	}
	else {
		get_exchange_rate(frm, frm.doc.date, frm.doc.currency, company_currency, function(exchange_rate) {
			frm.set_value("conversion_rate", exchange_rate);

			//exchange rate field label
			cur_frm.set_df_property("conversion_rate", "description", 
				"1 " + frm.doc.currency + " = " + exchange_rate + " " + company_currency);
		});
	}

	change_form_labels(frm);
	change_grid_labels(frm);
	frm.refresh_fields();
}
function get_exchange_rate(frm, transaction_date, from_currency, company_currency, callback) {
	var args;
	if (["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"].includes(frm.doctype)) {
		args = "for_selling";
	}
	else if (["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Stock In", "Payment Requistion"].includes(frm.doctype)) {
		args = "for_buying";
	}

	if (!transaction_date || !from_currency || !company_currency) return

	return frappe.call({
		method: "erpnext.setup.utils.get_exchange_rate",
		args: {
			transaction_date: transaction_date,
			from_currency: from_currency,
			to_currency: company_currency,
			args: args
		},
		freeze: true,
		freeze_message: __("Fetching exchange rates ..."),
		callback: function(r) {
			callback(flt(r.message));
		}
	});
}

function execute_workflow_from_server(frm) {
	// frappe.call({
	// 	method: 'before_save',
	// 	doc: frm.doc,
	// 	callback: function(r) {
	// 		if(r.message) {
	// 		}
	// 	}
	// });
}
function set_expense_items(frm) {
	$.each(frm.doc.expenses, function(i, d) { 
		let label = "";
		
		if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 
			
			if (cur_frm.doc.cost_center === "" || typeof cur_frm.doc.cost_center == 'undefined') {
				frappe.validated = false;
				frappe.msgprint("Set a Default Cost Center or specify the Cost Center for expense <strong>No. " 
								+ (i + 1) + "</strong>.");
				return false;
			}
			else {
				d.cost_center = cur_frm.doc.cost_center; 
			}
		}
	}); 
}


function warn_if_quotations_are_absent(frm) {
	// prompts the user to confirm if they want to proceed without quotations
	const action = frm.selected_workflow_action;
	if (['Request Executive Approval', 'Quotations Required'].includes(action) && (!frm.doc.first_quotation || !frm.doc.second_quotation || !frm.doc.third_quotation)) {
		frappe.dom.unfreeze(); // Unfreeze the screen to allow user interaction
		return new Promise((resolve, reject) => { 
			frappe.confirm(
				'Are you sure you want to <strong>' + action.toLowerCase() + '</strong> without any quotations?',
				function() {
					resolve();
				},
				function() {
					return false;
				}
			);
		});
	}
}

function validate_quotations(frm) {
	// prevents user from submitting the form without all the quotations if allow_incomplete_quotations is not checked
	if (['Quotations Required', 'Submitted to Accounts', 'Ready for Submission'].includes(frm.doc.workflow_state)) {
		if (frm.doc.allow_incomplete_quotations === 0 && (!frm.doc.first_quotation || !frm.doc.second_quotation || !frm.doc.third_quotation)) {
			frappe.dom.unfreeze();
			frappe.throw(__("Please upload all quotations or tick the <strong>Allow Incomplete Quotations</strong> checkbox. To proceed without all required quotations."));
		}
	}
}

function verify_workflow_action(frm) {
    const action = frm.selected_workflow_action;

    return new Promise((resolve, reject) => {
        frappe.dom.unfreeze(); // Unfreeze the form

        if (['Approve', 'Request Approval', 'Submit', 'Request Executive Approval'].includes(action)) {
            frappe.confirm(
                'Are you sure you want to <strong>' + action.toLowerCase() + '</strong>?',
                () => {
                    resolve();
                },
                () => {
                    reject(new Error("Action cancelled by user"));
                }
            );
        } else if (['Reject', 'Cancel', 'Request Revision', 'Request Employee Revision'].includes(action)) {
            console.log(3, "Reject/Cancel/Request Revision", action);
            
            frappe.prompt(
                {
                    fieldtype: 'Small Text',
                    fieldname: 'approval_comment',
                    label: __('Please provide a reason for this action'),
                    reqd: 1,
                    height: '10em'
                }, 
                data => {
                    if (data.approval_comment) {
                        frappe.call({
                            method: "frappe.client.set_value",
                            args: {
                                doctype: frm.doc.doctype,
                                name: frm.doc.name,
                                fieldname: 'approval_comment',
                                value: data.approval_comment
                            },
                            callback: function(response) {
                                if (response.message) {
                                    resolve();
                                } else {
                                    reject(new Error('Failed to set approval comment'));
                                }
                            }
                        });
                    } else {
                        frappe.validated = false;
                        reject(new Error("No comment provided"));
                    }
                }, 
                __('This action requires a comment'), 
                __('Submit')
            );
        } else {
            // For actions that don't require confirmation
            resolve();
        }

    });
}

frappe.ui.form.on("Payment Requisition", {
	
	before_workflow_action: async function(frm) {		
		// Workflow Action message capture and action verification 


        
		try {
            await warn_if_quotations_are_absent(frm);
            validate_quotations(frm);
            await verify_workflow_action(frm);
            // If all checks pass, the workflow action can proceed
        } catch (error) {
            console.log(error.message);
            frappe.validated = false;
			frappe.throw()
        }
		
		// if (frm.doc.workflow_state === 'Quotations Required' && (!frm.doc.first_quotation || !frm.doc.second_quotation || !frm.doc.third_quotation)) {
        //     frappe.dom.unfreeze(); // Unfreeze the screen to allow user interaction  
			
        //     return new Promise((resolve, reject) => {
        //         frappe.msgprint(
        //             'Quotations are required before submitting the Payment Requisition.'
        //         );
		// 		return false;
				
        //     });
        // }

    },
	currency: function(frm) {		
		let company_currency = get_company_currency(frm.doc.company);
		frm.toggle_display("conversion_rate", frm.doc.currency !== company_currency);
		check_currency(frm, company_currency);
	},
    validate: function(frm) {
        set_expense_items(frm);		
        
    },
	onload: function(frm) {
        set_queries(frm);
	},
	company: function(frm) {
        set_queries(frm);
        unset_cost_center(frm);
	},
	after_save: function(frm){
		frm.refresh_fields();
	},
    setup: function(frm) {
		frm.set_query("party_type", function () {
			frm.events.validate_company(frm);
			return {
				filters: {
					name: ["in", Object.keys(frappe.boot.party_account_types).filter(type => type !== "Customer" && type !== "Shareholder")],
				},
			};
		});		
	},

	refresh: function(frm) {
		erpnext.hide_company(frm);
		frm.events.show_general_ledger(frm);
		
		currency = get_company_currency(frm.doc.company)
		if (!frm.doc.currency){
			frm.set_value("currency", currency);
			frm.set_value("conversion_rate", 1);
			frm.refresh_fields();
		}
		// let company_currency = get_company_currency(frm.doc.company);
		// frm.toggle_display("conversion_rate", frm.doc.currency !== company_currency);
	},

	validate_company: (frm) => {
		if (!frm.doc.company) {
			frappe.throw({ message: __("Please select a Company first."), title: __("Mandatory") });
		}
	},

	company: function(frm) {
		frm.trigger("party");
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	// contact_person: function(frm) {
	// 	frm.set_value("contact_email", "");
	// 	erpnext.utils.get_contact_details(frm);
	// },

	show_general_ledger: function(frm) {
		if (frm.doc.workflow_state === "Payment Completed") {
			frm.add_custom_button(
				__("Ledger"),
				function () {
					frappe.route_options = {
						// voucher_no: frm.doc.name,
						party: frm.doc.party,
						from_date: frm.doc.date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						group_by: "Group by Voucher (Consolidated)",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				"fa fa-table"
			);
		}
	},
	payment_type: function(frm) {
			if (frm.doc.party) {
				frm.events.party(frm);
			}

			if (frm.doc.mode_of_payment) {
				frm.events.mode_of_payment(frm);
			}
	},
	party_type: function(frm) {
		let party_types = Object.keys(frappe.boot.party_account_types);
		if (frm.doc.party_type && !party_types.includes(frm.doc.party_type)) {
			frm.set_value("party_type", "");
			frappe.throw(__("Party can only be one of {0}", [party_types.join(", ")]));
		}

		frm.set_query("party", function () {
			if (frm.doc.party_type == "Employee") {
				return {
					query: "erpnext.controllers.queries.employee_query",
				};
			}
		});

		if (frm.doc.party) {
			$.each(
				[
					"party"
				],
				function (i, field) {
					frm.set_value(field, null);
				}
			);
		}
	}
});