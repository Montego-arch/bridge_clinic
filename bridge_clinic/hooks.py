app_name = "bridge_clinic"
app_title = "Bridge Clinic"
app_publisher = "Montego-Arch"
app_description = "App for Bridge CLinic workflows"
app_email = "mmanuelmiles@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "bridge_clinic",
# 		"logo": "/assets/bridge_clinic/logo.png",
# 		"title": "Bridge Clinic",
# 		"route": "/bridge_clinic",
# 		"has_permission": "bridge_clinic.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/bridge_clinic/css/bridge_clinic.css"
# app_include_js = "/assets/bridge_clinic/js/bridge_clinic.js"
app_include_js = "/assets/bridge_clinic/js/expense_claim.js"
# app_include_js = "/assets/bridge_clinic/js/purchase_order.js"
# app_include_js = "/assets/bridge_clinic/js/material_request.js"
# app_include_js = "/assets/bridge_clinic/js/request_for_quotation.js"
# app_include_js = "/assets/bridge_clinic/js/purchase_order.js"

# include js, css files in header of web template
# web_include_css = "/assets/bridge_clinic/css/bridge_clinic.css"
# web_include_js = "/assets/bridge_clinic/js/bridge_clinic.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "bridge_clinic/public/scss/website"

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
# app_include_icons = "bridge_clinic/public/icons.svg"

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
# 	"methods": "bridge_clinic.utils.jinja_methods",
# 	"filters": "bridge_clinic.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "bridge_clinic.install.before_install"
# after_install = "bridge_clinic.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "bridge_clinic.uninstall.before_uninstall"
# after_uninstall = "bridge_clinic.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "bridge_clinic.utils.before_app_install"
# after_app_install = "bridge_clinic.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "bridge_clinic.utils.before_app_uninstall"
# after_app_uninstall = "bridge_clinic.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bridge_clinic.notifications.get_notification_config"

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

override_doctype_class = {
	# "ToDo": "custom_app.overrides.CustomToDo",
	"Payment Request": "bridge_clinic.overrides.payment_request.CustomPaymentRequest",
	"Payment Entry": "bridge_clinic.overrides.payment_entry.CustomPaymentEntry"
}

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
    "Expense Claim": {
        "on_submit": "bridge_clinic.api.create_payment_request_for_expense"
    },
    "Payment Entry": {
        "on_submit": "bridge_clinic.api.notify_expense_payment_made"
    },
	    "Material Request": {
		"validate": "bridge_clinic.api.fill_suppliers_in_material_request",
        "on_submit": "bridge_clinic.api.create_rfq_from_material_request"
    },
	#     "Request for Quotation": {
    #     "on_submit": "bridge_clinic.api.create_po_from_rfq"
    # },
	    "Purchase Receipt": {
        "on_submit": "bridge_clinic.api.handle_purchase_receipt_on_submit_for_draft"
    },
	#     "Purchase Invoice": {
    #     "on_submit": "bridge_clinic.api.create_payment_request_from_pi"
    # }
	# ,
	    "Supplier Quotation": {
        "on_submit": "bridge_clinic.api.create_po_from_supplier_quotation"
    }
	,
	    "Purchase Order": {
        "on_submit": "bridge_clinic.api.create_payment_request_from_po"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"bridge_clinic.tasks.all"
# 	],
# 	"daily": [
# 		"bridge_clinic.tasks.daily"
# 	],
# 	"hourly": [
# 		"bridge_clinic.tasks.hourly"
# 	],
# 	"weekly": [
# 		"bridge_clinic.tasks.weekly"
# 	],
# 	"monthly": [
# 		"bridge_clinic.tasks.monthly"
# 	],
# }

# Testing
# -------
# run this when app loads


# before_tests = "bridge_clinic.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "bridge_clinic.event.get_events"
# }


#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "bridge_clinic.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["bridge_clinic.utils.before_request"]
# after_request = ["bridge_clinic.utils.after_request"]

# Job Events
# ----------
# before_job = ["bridge_clinic.utils.before_job"]
# after_job = ["bridge_clinic.utils.after_job"]

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

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"bridge_clinic.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Bridge Clinic"]]}
]