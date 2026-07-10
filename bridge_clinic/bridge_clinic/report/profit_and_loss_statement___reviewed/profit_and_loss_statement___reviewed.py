# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def execute(filters=None):
	# new: check for cost center column view
	if filters.get("show_cost_centers_in_columns"):
		return execute_cost_center_columns(filters)

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, filters.company
	)

	chart = get_chart_data(filters, columns, income, expense, net_profit_loss)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	report_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	)

	return columns, data, None, chart, report_summary


def execute_cost_center_columns(filters):
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	currency = filters.presentation_currency or company_currency

	cost_centers = get_selected_cost_centers(filters)
	if not cost_centers:
		frappe.throw(_("Please select at least one Cost Center to use this view."))

	columns = get_cost_center_columns(cost_centers, currency)

	# Use a single period for the whole date range
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		"Yearly",  # Consolidate into one period
		company=filters.company,
	)

	income_data, expense_data = get_data_for_cost_center_view(
		filters, cost_centers, period_list
	)

	# new: allocate costs if checkbox is checked
	if filters.get("allocate_costs"):
		income_data, expense_data = allocate_shared_costs(
			filters, income_data, expense_data, cost_centers
		)

	net_profit_loss = get_net_profit_loss_for_cost_center_view(
		income_data, expense_data, cost_centers, currency
	)

	data = []
	data.extend(income_data or [])
	data.extend(expense_data or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	return columns, data, None, None, None


def get_selected_cost_centers(filters):

    if not filters.get("cost_center"):
        return []

    return frappe.get_all(
        "Cost Center",
        filters={
            "name": ["in", filters.get("cost_center")]
        },
        fields=["name"],
        order_by="name"
    )


def get_cost_center_columns(cost_centers, currency):
	columns = [
		{"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 300},
	]
	for cc in cost_centers:
		columns.append(
			{
				"fieldname": cc.name,
				"label": cc.name,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)
	columns.append(
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Currency", "options": "currency", "width": 150}
	)
	return columns


def get_data_for_cost_center_view(filters, cost_centers, period_list):
	period_key = period_list[0].key
	income_data_map, expense_data_map = {}, {}

	for cc in cost_centers:
		cc_filters = filters.copy()
		cc_filters.cost_center = cc.name

		income = get_data(
			filters.company, "Income", "Credit", period_list, filters=cc_filters, ignore_closing_entries=True
		)
		expense = get_data(
			filters.company, "Expense", "Debit", period_list, filters=cc_filters, ignore_closing_entries=True
		)

		for row in income:
			if row.get("account"):
				account = row["account"]
				income_data_map.setdefault(account, row)[cc.name] = row.get(period_key, 0.0)

		for row in expense:
			if row.get("account"):
				account = row["account"]
				expense_data_map.setdefault(account, row)[cc.name] = row.get(period_key, 0.0)

	_calculate_row_totals(income_data_map, cost_centers)
	_calculate_row_totals(expense_data_map, cost_centers)

	return list(income_data_map.values()), list(expense_data_map.values())


def allocate_shared_costs(filters, income_data, expense_data, cost_centers):
	"""
	Allocate expenses from the selected Allocation Source Cost Center
	to all destination Cost Centers based on the Cost Center Allocation
	document.

	The source cost center DOES NOT require an allocation percentage.
	"""

	# ------------------------------------------------------------------
	# Get Source Cost Center from Report Filter
	# ------------------------------------------------------------------

	main_cc = filters.get("allocation_source_cost_center")

	if not main_cc:
		frappe.throw(_("Please select an Allocation Source Cost Center."))

	# ------------------------------------------------------------------
	# Find Allocation Document
	# ------------------------------------------------------------------

	allocation_doc = frappe.db.get_value(
		"Cost Center Allocation",
		{
			"main_cost_center": main_cc
		},
		"name"
	)

	if not allocation_doc:
		frappe.throw(
			_("No Cost Center Allocation found for {0}.").format(main_cc)
		)

	# ------------------------------------------------------------------
	# Read Allocation Percentages
	# ------------------------------------------------------------------

	allocation_rules = frappe.get_all(
		"Cost Center Allocation Percentage",
		filters={
			"parent": allocation_doc
		},
		fields=[
			"cost_center",
			"percentage"
		],
		order_by="idx"
	)

	if not allocation_rules:
		frappe.throw(
			_("No allocation percentages found for {0}.").format(main_cc)
		)

	# ------------------------------------------------------------------
	# Build Allocation Map
	# ------------------------------------------------------------------

	allocation_map = {}

	total_percentage = 0

	for rule in allocation_rules:

		# Ignore source cost center if it accidentally exists
		if rule.cost_center == main_cc:
			continue

		allocation_map[rule.cost_center] = flt(rule.percentage)

		total_percentage += flt(rule.percentage)

	if round(total_percentage, 2) != 100:
		frappe.throw(
			_("Allocation percentages must equal 100%. Current total is {0}%").format(total_percentage)
		)

	# ------------------------------------------------------------------
	# Allocate Expense Rows
	# ------------------------------------------------------------------

	for row in expense_data:

		if not row.get("account"):
			continue

		source_amount = flt(row.get(main_cc))

		if source_amount == 0:
			continue

		for destination_cc, percentage in allocation_map.items():

			# Only allocate to displayed Cost Centers
			if destination_cc not in row:
				continue

			allocated_amount = source_amount * percentage / 100

			row[destination_cc] = (
				flt(row.get(destination_cc))
				+ allocated_amount
			)

		# Remove amount from source Cost Center
		row[main_cc] = 0

	# ------------------------------------------------------------------
	# Recalculate Totals
	# ------------------------------------------------------------------

	expense_data_map = {
		row["account"]: row
		for row in expense_data
		if row.get("account")
	}

	_calculate_row_totals(expense_data_map, cost_centers)

	return income_data, list(expense_data_map.values())


def get_report_summary(
	period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	if filters.accumulated_values:
		# when 'accumulated_values' is enabled, periods have running balance.
		# so, last period will have the net amount.
		key = period_list[-1].key
		if income:
			net_income = income[-2].get(key)
		if expense:
			net_expense = expense[-2].get(key)
		if net_profit_loss:
			net_profit = net_profit_loss.get(key)
	else:
		for period in period_list:
			key = period if consolidated else period.key
			if income:
				net_income += income[-2].get(key)
			if expense:
				net_expense += expense[-2].get(key)
			if net_profit_loss:
				net_profit += net_profit_loss.get(key)

	if len(period_list) == 1 and periodicity == "Yearly":
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
	else:
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")

	return [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	]


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_net_profit_loss_for_cost_center_view(income, expense, cost_centers, currency):
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency,
	}

	total_income_row = income[-2] if income else {}
	total_expense_row = expense[-2] if expense else {}
	grand_total = 0

	for cc in cost_centers:
		cc_name = cc.name
		profit = flt(total_income_row.get(cc_name)) - flt(total_expense_row.get(cc_name))
		net_profit_loss[cc_name] = profit

	total_profit = flt(total_income_row.get("total")) - flt(total_expense_row.get("total"))
	net_profit_loss["total"] = total_profit

	return net_profit_loss


def _calculate_row_totals(data_map, cost_centers):
	for row in data_map.values():
		total = 0
		for cc in cost_centers:
			total += flt(row.get(cc.name))
		row["total"] = total

def get_chart_data(filters, columns, income, expense, net_profit_loss):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	for p in columns[2:]:
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))

	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"

	return chart
