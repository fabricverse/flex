import frappe
from frappe.model.document import Document


@frappe.whitelist()
def approve(doc, method):
    # define important variables
    curr_user = frappe.session.user
    cache_key = f"approvers_for_{doc.doctype}_{doc.name}"
    approvers = frappe.cache().get_value(cache_key) or []
    wrk_state_changed = doc.has_value_changed("workflow_state")


    if wrk_state_changed and doc.workflow_state != "Open" and doc.workflow_state != "Rejected":
        approver_record = doc.get("approvers",{
            "approver": curr_user,
            "approval_status": ""
        })
        if approver_record:
            # User has already taken an action
            if approver_record.approval_status == "Approved":
                # User is trying to approve again
                frappe.throw("User has already approved")
            else:
                # User is changing their mind from rejected to approved
                approver_record.approval_status = "Approved"
        else:
            # User is approving for the first time
            approvers.append(curr_user)
            doc.append("approvers", {
                "approver": curr_user,
                "approval_status": "Approved"
            })
    elif wrk_state_changed and doc.workflow_state == "Rejected":
        doc.append("approvers",{
            "approver": curr_user,
            "approval_status": "Rejected"
        })

    frappe.cache().set_value(cache_key, approvers)


