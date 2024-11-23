app_name = "flex"
app_title = "Flex"
app_publisher = "Fabric"
app_description = "Flexible Expenses"
app_email = "devs@thebantoo.com"
app_license = "mit"

import frappe
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/flex/css/flex.css"
# app_include_js = "/assets/flex/js/flex.js"

# include js, css files in header of web template
# web_include_css = "/assets/flex/css/flex.css"
# web_include_js = "/assets/flex/js/flex.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "flex/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "flex/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "flex.utils.jinja_methods",
# 	"filters": "flex.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "flex.install.before_install"
# after_install = "flex.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "flex.uninstall.before_uninstall"
# after_uninstall = "flex.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "flex.utils.before_app_install"
# after_app_install = "flex.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "flex.utils.before_app_uninstall"
# after_app_uninstall = "flex.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "flex.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
	"Expense Entry": {
		"on_update": "flex.app.setup"
	},
	"Email Queue": {
		"after_insert": "flex.app.add_doc_attachments"
	},
	"Expense Request": {
		"validate": "flex.approve_expense.approve"
	},
	"Project": {
		"after_insert": "flex.app.create_project_cost_center"
	}
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "cron": {
        "* * * * *": [
            "frappe.email.queue.flush"
        ]
    }
}

# scheduler_events = {
# 	"all": [
# 		"flex.tasks.all"
# 	],
# 	"daily": [
# 		"flex.tasks.daily"
# 	],
# 	"hourly": [
# 		"flex.tasks.hourly"
# 	],
# 	"weekly": [
# 		"flex.tasks.weekly"
# 	],
# 	"monthly": [
# 		"flex.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "flex.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "flex.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "flex.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["flex.utils.before_request"]
# after_request = ["flex.utils.after_request"]

# Job Events
# ----------
# before_job = ["flex.utils.before_job"]
# after_job = ["flex.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Fixtures
# --------
# move perms to mpz app

fixtures = [        
    {
        "doctype": "Role",
        "filters": {
            "role_name": ["in", [
                "All Finance",
                "First Approver",
                "Final Approver",
                "Board Director",
                "Director",
                "Executive Director",
                "Volunteer",
                "Employee Self Service"
            ]]
        }
    },    
    {
        "doctype": "Property Setter",
        "filters": {
            "doc_type": ["in", [
                "Cost Center",
                "Account",
                "Project",
                "Supplier",
                "Task",
                "User",
                "Mode of Payment",
                "Task",
                "Activity Type",
                "Volunteer Log",
                "Journal Entry",
                "Payment Requisition",
                "Payment Requisition Settings",
                "Expense Item",
                "Document Series",
                "File"
            ]]
        }
    },
    {
        "doctype": "Custom DocPerm",
        "filters": {
            "parent": ["in", [
                "Cost Center",
                "Account",
                "Project",
                "Supplier",
                "Task",
                "User",
                "Mode of Payment",
                "Task",
                "Activity Type",
                "Volunteer Log",
                "Journal Entry",
                "Payment Requisition",
                "Payment Requisition Settings",
                "Expense Item",
                "Document Series",
                "File"
            ]]
        }
    },
    {
        "doctype": "Workflow State",
        "filters": {
            "workflow_state_name": ["in", [
                "Attachments Required",
                "Submitted to Accounts",
                "Employee Revision Required",
                "Pending Internal Check",
                "Pending First Approval",
                "Pending Final Approval",
                "Payment Due",
                "Capture Expenses",
                "Revision Requested",
                "Expense Revision",
                "Accounts Verification",
                "Cancelled",
                "Queried",
                "Rejected",
                "Closed",
            ]]
        }
    },
    {
        "doctype": "Workflow Action Master",
        "filters": {
            "workflow_action_name": ["in", [
                "Accept Entries",
                "Request Expense Revision",
                "Request Executive Approval",
                "Request Employee Revision",
                "Request Requester Revision",
                "Query",
                "Cancel",
                "Revise",
                "Request Approval",
                "Save",
                "Revert to Accounts"
            ]]
        }
    },
    {
        "doctype": "Workflow",
        "filters": {
            "document_type": ["in", ["Payment Requisition"]]
        }
    },
    {
        "doctype": "Notification",
        "filters": {
            "name": ["in", [
                "Requisition Workflow Action Required", 
                "Payment Requisition Approval",
                "Payment Requisition Payment",
                "Requisition Approval Query"
            ]]
        }
    }
]



# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"flex.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

