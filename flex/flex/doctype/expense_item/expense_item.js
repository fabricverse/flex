// Copyright (c) 2024, Fabric and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Item", {
    validate(frm){
        // set payable account as default account if use_default_payable_account is checked
        if (frm.doc.use_default_payable_account === 1 && !frm.doc.payable_account) {
            frappe.call({
                method: 'doc_setup',
                doc: frm.doc,
                callback: function (r) {
                    frm.refresh_fields();
                }
            });
        }
    },
    setup(frm){
        if (frm.doc.default_payable_account) return;

        frappe.call({
            method: 'set_default_account',
            doc: frm.doc,
            callback: function (r) {
                frm.refresh_fields();
            }
        });
    },	
    refresh(frm) {
        set_default_account(frm);
	},
    use_default_payable_account(frm){
        if (frm.doc.use_default_payable_account === 0) {
            frm.set_value('payable_account', '');
        }
        else {
            set_default_account(frm);
        }
    }
});

function set_default_account(frm) {
    if (frm.doc.use_default_payable_account===0 || frm.doc.payable_account) {
        console.log("returning")
        return
        
    }
    frappe.call({
        method: 'doc_setup',
        doc: frm.doc,
        callback: function (r) {
            frm.refresh_fields();
        }
    });
}
