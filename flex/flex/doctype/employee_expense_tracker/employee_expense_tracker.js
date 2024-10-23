// Copyright (c) 2024, Fabric and contributors
// For license information, please see license.txt

function update_totals(frm, cdt, cdn){
	var items = locals[cdt][cdn];
    var total = 0;
    var total_qty = 0;
    frm.doc.expenses.forEach(
        function(items) { 
            total += items.amount;
            total_qty +=1;
        });
    frm.set_value("total", total);
    refresh_field("total");
    frm.set_value("total_qty", total_qty);
    refresh_field("total_qty");
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
frappe.ui.form.on("Employee Expense Tracker", {

    payment_requisition: function(frm){
        frm.dashboard.reset();
        add_dashboard_data(frm);
    },
    after_submit: function(frm){
        frm.dashboard.reset();
        add_dashboard_data(frm);
    },
    refresh(frm){
        add_dashboard_data(frm);

        frm.add_custom_button(
            __("Get Requisition Items"),
            function () {
                map_employee_expense_to_payment_requisition({
                    method: "flex.flex.doctype.payment_requisition.payment_requisition.make_payment_requisition",
                    source_doctype: "Payment Requisition",
                    target: frm,
                    setters: {
                        // name: undefined,
                        date: undefined,
                        party: frm.doc.employee,
                        activity: frm.doc.activity || undefined,
                        project_name: frm.doc.project || undefined,
                        total: undefined
                    },
                    get_query_filters: {
                        docstatus: 1,
                        status: ["not in", ["Closed", "Completed"]],
                        company: frm.doc.company
                    },
                });
            }
        );
        
    }
});


function map_employee_expense_to_payment_requisition(opts) {
    function _map() {
        console.log("Mapping expenses to payment requisition 2");

        return frappe.call({
            type: "POST",
            method: "frappe.model.mapper.map_docs",
            args: {
                method: opts.method,
                source_names: opts.source_name,
                target_doc: cur_frm.doc,
                args: opts.args,
            },
            freeze: true,
            freeze_message: __("Mapping {0} ...", [opts.source_doctype]),
            callback: function (r) {
                if (!r.exc) {
                    frappe.model.sync(r.message);
                    cur_frm.dirty();
                    cur_frm.refresh();
                }
            },
        });
    }

    let query_args = {};
    if (opts.get_query_filters) {
        query_args.filters = opts.get_query_filters;
    }

    if (opts.get_query_method) {
        query_args.query = opts.get_query_method;
    }

    if (query_args.filters || query_args.query) {
        opts.get_query = () => query_args;
    }

    if (opts.source_doctype) {
        const d = new frappe.ui.form.MultiSelectDialog({
            doctype: opts.source_doctype,
            target: opts.target,
            setters: opts.setters,
            get_query: opts.get_query,
            add_filters_group: 1,
            action: function (selections) {
                let values = selections;

                if (values.length === 0) {
                    frappe.msgprint(__("Please select {0}", [opts.source_doctype]));
                    return;
                }
                else if (values.length > 1) {
                    frappe.msgprint(__("Please select only one {0}", [opts.source_doctype]));
                    return;
                }

                // Fetch expenses for each selected document
                // frappe.call({
                //     method: "frappe.client.get",
                //     args: {
                //         doctype: opts.source_doctype,
                //         name: values[0]  // Assuming only one selection is allowed
                //     },
                //     callback: function(r) {
                //         if (r.message) {
                //             const expenses = r.message.expenses || [];

                //             const filteredExpenses = expenses

                //             if (cur_frm.doc.expenses.length > 0){
                //                 // Filter out already existing expenses
                //                 const filteredExpenses = expenses.filter(expense => !isExpenseAlreadyMapped(expense));
                //             }

                //             opts.source_name = [...new Set(filteredExpenses.map(expense => expense.name))];
                //             d.dialog.hide();
                //             _map();
                //         }
                //     }
                // });
                opts.source_name = [...new Set(values)];
                d.dialog.hide();
                _map();
            },
        });

        return d;
    }

    if (opts.source_name) {
        opts.source_name = [opts.source_name];
        _map();
    }
}

// Helper function to check if an expense is already mapped
function isExpenseAlreadyMapped(expense) {
    // Assuming `cur_frm.doc.expenses` contains the list of already mapped expenses
    console.log("Checking if expense is already mapped", expense, expense.amount, expense.description, expense.expense_item);

    const result = cur_frm.doc.expenses.some(existingExpense => 
        existingExpense.amount === expense.amount &&
        existingExpense.description === expense.description &&
        existingExpense.expense_item === expense.expense_item
    );
    console.log("Expense is already mapped", result);
    return result;
}


function add_dashboard_data(frm){
    let total_expenditure = 0;
        let total_allocated = 0;
        
        frappe.call({
            method: "get_dashboard_data",
            doc: frm.doc,
            callback: function(r) {
                
                total_allocated = r.message.total_allocated || 0;
                total_expenditure = r.message.total_expenditure || 0;

                // dashboard class https://github.com/frappe/frappe/blob/60df96ce0850d8952eb810070b5e8faf12e37aaa/frappe/public/js/frappe/form/dashboard.js#L6
                frm.dashboard.add_indicator(
                    __("Total Allocated: {0}", [
                        format_currency(
                            total_allocated,
                            "USD"
                        ),
                    ]),
                    "blue"
                );
                frm.dashboard.add_indicator(
                    __("Total Unsettled: {0}", [
                        format_currency(
                            total_allocated - total_expenditure,
                            "USD"
                        ),
                    ]),
                    total_expenditure < total_allocated ? "orange" : "green"
                );
                
                if (frm.docstatus == 0) {
                    projection_amt = (total_allocated - (total_expenditure+frm.doc.total))
                    frm.dashboard.show_progress(
                        "Projection", 100 - (projection_amt/total_allocated * 100), "Projected Requisition Expenditure"
                    );
                }
                else {
                    frm.dashboard.show_progress(
                        "Expenditure", 100 - (total_expenditure/total_allocated * 100), "Total Requisition Expenditure"
                    );
                }
            }
        });
}
