// Copyright (c) 2024, Fabric and contributors
// For license information, please see license.txt
function toggle_display_sections(frm) {
	// hide all other fields except for the ones applicable to the workflow state
	all_sections = [
		'section_transaction', 'section_currency', 'section_posting', 'section_request_items', 'section_request_totals', 
		'section_attachments', 'section_remarks',
		'section_expense_items', 'section_expense_totals', 'section_deposit',
		'section_info', 'section_approvers', 'section_history'
	];
	not_set = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks'];
	quotation_required_sections = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks'];
	submitted_to_accounts_sections = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks', 'section_history'];
	approvers = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks', 'section_history', 'section_approvers'];
	payment_due = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks', 'section_history', 'section_approvers'];
	capture_expenses = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks', 'section_history', 'section_approvers', 'section_expense_items', 'section_expense_totals', 'section_deposit', 'section_info'];

	let display_sections = [];
	let condition = false;
	if (!frm.doc.workflow_state){ // before wf is set
		display_sections = all_sections.filter(field => !not_set.includes(field));
		// console.log("no workflow set", frm.doc.workflow_state)
	}
	else if (frm.doc.workflow_state === 'Quotations Required'){
		display_sections = all_sections.filter(field => !quotation_required_sections.includes(field));
	}
	else if (['Submitted to Accounts', 'Employee Revision Required'].includes(frm.doc.workflow_state)){ // 
		display_sections = all_sections.filter(field => !submitted_to_accounts_sections.includes(field));
	}
	else if (['Awaiting Internal Approval', 'Awaiting Director Approval (1)', 'Awaiting Director Approval (2)', 'Payment Due'].includes(frm.doc.workflow_state)){ // 
		display_sections = all_sections.filter(field => !approvers.includes(field));
	}
	else if (frm.doc.workflow_state === 'Payment Due'){
		display_sections = all_sections.filter(field => !payment_due.includes(field));
	}
	// else if (['Capture Expenses', 'Accounts Approval', 'Closed'].includes(frm.doc.workflow_state)){
	// 	display_sections = all_sections.filter(field => !capture_expenses.includes(field));
	// }
	else {
		// show all
		display_sections = all_sections;
		condition = true;
	}

	// console.log("display_sections", display_sections, frm.doc.workflow_state);
	
	return {
		fields: display_sections,
		condition: condition
	};
}

frappe.ui.form.on("Payment Requisition", {
	btn_reset_deposit: function(frm) {
		frm.set_value("deposit_amount", 0);
		frm.refresh_field("deposit_amount");
	},
	skip_proof: function(frm){
		frm.refresh_field("expense_items");
	},
	btn_deposit_remainder: function(frm) {
		// Deposit the remainder of the requisition amount to the bank account
		// Refresh the field to show the updated table
		let deposit_amount = frm.doc.total - frm.doc.total_expenditure;
		if (deposit_amount <= 0) {
			deposit_amount = 0;
		}
		frm.set_value("deposit_amount", deposit_amount);
		frm.refresh_field("expense_items");
		frm.refresh_field("deposit_amount");
	},
	after_workflow_action: function(frm) {
		// TODO: move to py
		// if (["Submitted to Accounts", "Awaiting Internal Approval", "Awaiting Director Approval (1)", "Awaiting Director Approval (2)"].includes(frm.doc.workflow_state)) {
		// 	frm.set_value("skip_proof", 0);
		// 	frm.set_value("allow_incomplete_quotations", 0);
		// 	frm.refresh_field("skip_proof");
		// 	frm.refresh_field("allow_incomplete_quotations");
		// }
		
		// console.log('refreshed')
		// frm.refresh();
	},
	refresh: function(frm) {
		let {fields, condition} = toggle_display_sections(frm);
		frm.toggle_display(fields, condition);

		fields.forEach(field => refresh_field(field));
		
		frm.get_field("btn_deposit_remainder").$input.addClass("btn-primary");
		frm.get_field("btn_reset_deposit").$input.addClass("btn-danger");

		if (["Payment Due", "Rejected", "Cancelled", "Accounts Approval", "Closed", "Expense Revision"].includes(frm.doc.workflow_state)) {
			cur_frm.fields_dict['section_attachments'].collapse(1)
		}

		// get_sections_to_hide(frm)
		// all_sections = [
		// 	'section_transaction', 'section_currency', 'section_posting', 'section_request_items', 'section_request_totals', 
		// 	'section_attachments', 'section_remarks',
		// 	'section_expense_items', 'section_expense_totals', 'section_deposit',
		// 	'section_info', 'section_approvers', 'section_history'
		// ];
		// quotation_required_sections = ['section_transaction', 'section_request_items', 'section_request_totals', 'section_currency', 'section_posting', 'section_attachments', 'section_remarks'];

		// display_sections = all_sections.filter(field => !quotation_required_sections.includes(field));
		// console.log("display_sections", display_sections);

		
		// frm.toggle_display(display_sections, frm.doc.workflow_state !== 'Quotations Required');
		
		// deposit_button = frm.fields_dict["expense_items"].grid.add_custom_button(__('Deposit Remainder'),
		// 	function() {
		// 		// Deposit the remainder of the requisition amount to the bank account
		// 		// Refresh the field to show the updated table
		// 		let deposit_amount = frm.doc.total - frm.doc.total_expenditure;
		// 		if (deposit_amount <= 0) {
		// 			deposit_amount = 0;
		// 		}
		// 		frm.set_value("deposit_amount", deposit_amount);
		// 		frm.refresh_field("expense_items");
		// 		frm.refresh_field("deposit_amount");
		// 	}
		// );
		// deposit_button.removeClass('btn-default').addClass('btn-primary');
		if (["Capture Expenses", "Accounts Approval", "Expense Revision"].includes(frm.doc.workflow_state)){
			frm.fields_dict["expense_items"].grid.add_custom_button(__('Add Requisition Items'), 
				function() {
					// Copy items from (requested) request_items to expense_items
					frm.doc.request_items.forEach(item => {
						// Check if the item already exists in expense_items
						const exists = frm.doc.expense_items.some(existing_expense => 
							existing_expense.expense_item === item.expense_item &&
							existing_expense.expense_account === item.expense_account // && existing_expense.amount === item.amount
						);
						// If it doesn't exist, add it
						if (!exists) {
							let new_row = frm.add_child("expense_items");
							new_row.expense_item = item.expense_item;
							new_row.description = item.description;
							new_row.expense_account = item.expense_account;
							new_row.amount = item.amount;
							new_row.cost_center = item.cost_center;
							new_row.project = item.project;
							new_row.activity = item.activity;
						}
					});
					update_expense_totals();

					let deposit_amount = 0;
					if (frm.doc.deposit_amount > 0) {
						deposit_amount = frm.doc.total - frm.doc.total_expenditure;
					}

					frm.set_value("deposit_amount", deposit_amount);
					frm.refresh_field("deposit_amount");

					// Refresh the field to show the updated table
					frm.refresh_field("expense_items");
				}
			);
			frm.fields_dict["expense_items"].grid.grid_buttons.find('.btn-custom').removeClass('btn-default').addClass('btn-primary');

		}
		// frm.dashboard.show_progress(
		//     "Requisition Expenditure", ((frm.doc.total-frm.doc.total_expenditure)/frm.doc.total * 100)
		// );
		erpnext.hide_company(frm);
		frm.events.show_general_ledger(frm);
		
		currency = get_company_currency(frm.doc.company)
		if (!frm.doc.currency){
			frm.set_value("currency", currency);
			frm.set_value("conversion_rate", 1);
			frm.refresh_fields();
		}

		// Hide workflow actions button for specific states
		if (frm.doc.workflow_state === "Approved" || frm.doc.workflow_state === "Payment Completed") {
			frm.page.clear_actions_menu();
		}
	},
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
		check_currency(frm, company_currency);
		frm.toggle_display("conversion_rate", frm.doc.currency !== company_currency);
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
	},

	make_employee_expense_tracker: function (frm) {
		frappe.model.open_mapped_doc({
			method: "flex.flex.doctype.payment_requisition.payment_requisition.make_employee_expense_tracker",
			frm: frm,
			freeze_message: __("Creating Employee Expense .. ."),
		});
	},
});

frappe.ui.form.on('Expense Entry Item', {
	amount: function(frm, cdt, cdn) {
        update_requisition_totals(frm, cdt, cdn);
	},
	request_items_remove: function(frm, cdt, cdn){
        update_requisition_totals(frm, cdt, cdn);
	},
    request_items_add: function(frm, cdt, cdn){
        var d = locals[cdt][cdn];
        
        if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 

            if (cur_frm.doc.cost_center != "" || typeof cur_frm.doc.cost_center != 'undefined') {
                
                d.cost_center = cur_frm.doc.cost_center; 
                cur_frm.refresh_field("request_items");
            }
        }
	}
});

frappe.ui.form.on('Requisition Expense Item', {
    expense_items_add: function(frm, cdt, cdn){
        var d = locals[cdt][cdn];

        if((d.activity === "" || typeof d.activity == 'undefined')) { 

            if (cur_frm.doc.activity != "" || typeof cur_frm.doc.activity != 'undefined') {
                
				d.activity = cur_frm.doc.activity; 
                cur_frm.refresh_field("expense_items");
            }
        }
        
        if((d.project === "" || typeof d.project == 'undefined')) { 

            if (cur_frm.doc.project != "" || typeof cur_frm.doc.project != 'undefined') {
                
				d.project = cur_frm.doc.project; 
                cur_frm.refresh_field("expense_items");
            }
        }

        if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 

            if (cur_frm.doc.cost_center != "" || typeof cur_frm.doc.cost_center != 'undefined') {
                
                d.cost_center = cur_frm.doc.cost_center; 
                cur_frm.refresh_field("expense_items");
            }
        }
	},
	amount: function(frm, cdt, cdn) {
        update_expense_totals();
	},
	expense_items_remove: function(frm, cdt, cdn){
        update_expense_totals();
	}
});


function update_expense_totals(){
    var total_expenditure = 0;
    cur_frm.doc.expense_items.forEach(
        function(item) { 
            total_expenditure += item.amount;
        });
    cur_frm.set_value("total_expenditure", total_expenditure);
    refresh_field("total_expenditure");
}

function update_requisition_totals(frm, cdt, cdn){
    var total = 0;
    var total_qty = 0;
    frm.doc.request_items.forEach(
        function(item) { 
            total += item.amount;
            total_qty +=1;
        });
    frm.set_value("total", total);
    refresh_field("total");
    frm.set_value("total_qty", total_qty);
    refresh_field("total_qty");
}

function set_queries(frm) {
    frm.set_query("expense_account", 'request_items', () => {
        return {
            filters: [
                ["Account", "root_type", "=", "Expense"],
                ["Account", "is_group", "=", "0"],
                ["Account", "company", "=", frm.doc.company]
            ]
        }
    });
    frm.set_query("cost_center", 'request_items', () => {
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
	if (frm.doc.request_items && frm.doc.request_items.length > 0) {
		frm.set_currency_labels(["amount"], frm.doc.currency, "request_items");
	}
}

function check_currency(frm, company_currency){
	frm.set_value("conversion_rate", 1);

	if (frm.doc.currency === company_currency || !frm.doc.currency) {
		frm.set_value("currency", company_currency);
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
	$.each(frm.doc.request_items, function(i, d) { 
		let label = "";
		
		if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 
			
			if (cur_frm.doc.cost_center === "" || typeof cur_frm.doc.cost_center == 'undefined') {
				frappe.validated = false;
				frappe.msgprint("Set a Default Cost Center or specify the Cost Center for expense item <strong>No. " 
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
			frappe.throw(__("Please upload all quotations or tick the <strong>Save with incomplete quotations</strong> checkbox. To proceed without all required quotations."));
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
        } else if (['Reject', 'Cancel', 'Request Revision', 'Request Employee Revision', 'Request Expense Revision'].includes(action)) {
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
						// frm.set_value('approval_comment', data.approval_comment)
						// frm.set_value('workflow_state', )
						frm.refresh_field('approval_comment')
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



