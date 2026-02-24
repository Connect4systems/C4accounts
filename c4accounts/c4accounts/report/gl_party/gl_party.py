import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 140,
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 180,
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 170,
        },
        {
            "label": _("Party Type"),
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Dynamic Link",
            "options": "party_type",
            "width": 140,
        },
        {
            "label": _("Party Name"),
            "fieldname": "party_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Balance"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Small Text",
            "width": 260,
        },
    ]


def get_data(filters):
    opening_debit, opening_credit = get_opening_totals(filters)
    opening_balance = opening_debit - opening_credit

    conditions, values = get_conditions(filters)
    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(
        f"""
        SELECT
            gle.posting_date,
            gle.company,
            gle.account,
            gle.voucher_type,
            gle.voucher_no,
            gle.party_type,
            gle.party,
            CASE
                WHEN gle.party_type = 'Customer' THEN customer.customer_name
                WHEN gle.party_type = 'Supplier' THEN supplier.supplier_name
                WHEN gle.party_type = 'Employee' THEN employee.employee_name
                ELSE gle.party
            END AS party_name,
            gle.debit,
            gle.credit,
            (gle.debit - gle.credit) AS line_balance,
            gle.remarks
        FROM `tabGL Entry` gle
        LEFT JOIN `tabCustomer` customer
            ON gle.party_type = 'Customer' AND gle.party = customer.name
        LEFT JOIN `tabSupplier` supplier
            ON gle.party_type = 'Supplier' AND gle.party = supplier.name
        LEFT JOIN `tabEmployee` employee
            ON gle.party_type = 'Employee' AND gle.party = employee.name
        WHERE {where_clause}
        ORDER BY gle.posting_date, gle.creation, gle.name
        """,
        values,
        as_dict=True,
    )

    period_debit = sum((row.debit or 0) for row in data)
    period_credit = sum((row.credit or 0) for row in data)
    period_balance = period_debit - period_credit

    closing_debit = opening_debit + period_debit
    closing_credit = opening_credit + period_credit
    closing_balance = opening_balance + period_balance

    running_balance = opening_balance
    for row in data:
        running_balance += (row.debit or 0) - (row.credit or 0)
        row.balance = running_balance
        row.pop("line_balance", None)

    result = []
    if filters.get("from_date"):
        result.append(
            {
                "posting_date": filters.from_date,
                "company": filters.get("company"),
                "account": filters.get("account"),
                "voucher_type": _("Opening"),
                "voucher_no": "",
                "party_type": filters.get("party_type"),
                "party": filters.get("party"),
                "party_name": "",
                "debit": opening_debit,
                "credit": opening_credit,
                "balance": opening_balance,
                "remarks": _("Opening Balance"),
            }
        )

    result.extend(data)

    result.append(
        {
            "posting_date": None,
            "company": filters.get("company"),
            "account": filters.get("account"),
            "voucher_type": _("Totals"),
            "voucher_no": "",
            "party_type": filters.get("party_type"),
            "party": filters.get("party"),
            "party_name": "",
            "debit": period_debit,
            "credit": period_credit,
            "balance": period_balance,
            "remarks": _("Period Totals"),
        }
    )

    result.append(
        {
            "posting_date": filters.get("to_date") or filters.get("from_date"),
            "company": filters.get("company"),
            "account": filters.get("account"),
            "voucher_type": _("Closing"),
            "voucher_no": "",
            "party_type": filters.get("party_type"),
            "party": filters.get("party"),
            "party_name": "",
            "debit": closing_debit,
            "credit": closing_credit,
            "balance": closing_balance,
            "remarks": _("Closing Balance"),
        }
    )

    return result


def get_conditions(filters):
    conditions = ["1=1", "ifnull(gle.is_cancelled, 0) = 0"]
    values = {}

    if filters.get("company"):
        conditions.append("gle.company = %(company)s")
        values["company"] = filters.company

    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
        values["from_date"] = filters.from_date

    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
        values["to_date"] = filters.to_date

    if filters.get("account"):
        conditions.append("gle.account = %(account)s")
        values["account"] = filters.account

    if filters.get("voucher_type"):
        conditions.append("gle.voucher_type = %(voucher_type)s")
        values["voucher_type"] = filters.voucher_type
    else:
        conditions.append("gle.voucher_type in ('Journal Entry', 'Payment Entry')")

    if filters.get("voucher_no"):
        conditions.append("gle.voucher_no = %(voucher_no)s")
        values["voucher_no"] = filters.voucher_no

    if filters.get("party_type"):
        conditions.append("gle.party_type = %(party_type)s")
        values["party_type"] = filters.party_type

    if filters.get("party"):
        conditions.append("gle.party = %(party)s")
        values["party"] = filters.party

    return conditions, values


def get_opening_totals(filters):
    if not filters.get("from_date"):
        return 0, 0

    conditions, values = get_conditions(filters)
    conditions = [
        condition
        for condition in conditions
        if condition
        not in (
            "gle.posting_date >= %(from_date)s",
            "gle.posting_date <= %(to_date)s",
            "gle.voucher_no = %(voucher_no)s",
        )
    ]
    conditions.append("gle.posting_date < %(from_date)s")
    values.pop("to_date", None)
    values.pop("voucher_no", None)
    values["from_date_opening"] = values["from_date"]

    conditions.pop()
    conditions.append(
        "(gle.posting_date < %(from_date_opening)s OR (gle.posting_date = %(from_date_opening)s AND ifnull(gle.is_opening, 'No') = 'Yes'))"
    )
    values.pop("from_date", None)

    where_clause = " AND ".join(conditions)

    opening = frappe.db.sql(
        f"""
        SELECT
            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit
        FROM `tabGL Entry` gle
        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )[0]

    return (opening.debit or 0), (opening.credit or 0)
