import calendar
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate


MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

STATUS_ABBR = {
    "Present": "P",
    "Absent": "A",
    "On Leave": "L",
    "Half Day": "HD",
    "Work From Home": "WFH",
    "Holiday": "H",
    "Weekly Off": "WO",
}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    from_date, to_date = get_date_range(filters)
    employees = get_employees(filters)

    day_columns = get_day_columns(from_date, to_date)
    columns = get_columns(day_columns)

    if not employees:
        return columns, []

    attendance_map = get_attendance_map([employee.name for employee in employees], from_date, to_date)
    holiday_map = get_holiday_map(employees, filters.company, from_date, to_date)

    data = get_data(employees, day_columns, attendance_map, holiday_map)
    return columns, data


def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))

    if not filters.get("month") or filters.month not in MONTHS:
        frappe.throw(_("Please select a valid month"))

    if not filters.get("year") or cint(filters.year) <= 0:
        frappe.throw(_("Please enter a valid year"))


def get_date_range(filters):
    year = cint(filters.year)
    month = MONTHS[filters.month]
    last_day = calendar.monthrange(year, month)[1]

    from_date = getdate(f"{year}-{month:02d}-01")
    to_date = getdate(f"{year}-{month:02d}-{last_day:02d}")
    return from_date, to_date


def get_day_columns(from_date, to_date):
    day_columns = []
    current_date = from_date

    while current_date <= to_date:
        day_columns.append(
            {
                "label": str(current_date.day),
                "fieldname": f"d_{current_date.day}",
                "fieldtype": "Data",
                "width": 45,
                "date": current_date,
            }
        )
        current_date += timedelta(days=1)

    return day_columns


def get_columns(day_columns):
    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 140,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 140,
        },
    ]

    columns.extend(
        {
            "label": column["label"],
            "fieldname": column["fieldname"],
            "fieldtype": column["fieldtype"],
            "width": column["width"],
        }
        for column in day_columns
    )

    columns.extend(
        [
            {
                "label": _("P"),
                "fieldname": "total_present",
                "fieldtype": "Int",
                "width": 55,
            },
            {
                "label": _("A"),
                "fieldname": "total_absent",
                "fieldtype": "Int",
                "width": 55,
            },
            {
                "label": _("L"),
                "fieldname": "total_leave",
                "fieldtype": "Int",
                "width": 55,
            },
            {
                "label": _("HD"),
                "fieldname": "total_half_day",
                "fieldtype": "Int",
                "width": 60,
            },
            {
                "label": _("WO"),
                "fieldname": "total_weekly_off",
                "fieldtype": "Int",
                "width": 60,
            },
            {
                "label": _("H"),
                "fieldname": "total_holiday",
                "fieldtype": "Int",
                "width": 55,
            },
        ]
    )

    return columns


def get_employees(filters):
    employee_filters = {
        "status": "Active",
        "company": filters.company,
    }

    if filters.get("employee"):
        employee_filters["name"] = filters.employee

    if filters.get("department"):
        employee_filters["department"] = filters.department

    if filters.get("designation"):
        employee_filters["designation"] = filters.designation

    return frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=["name", "employee_name", "department", "designation", "holiday_list"],
        order_by="name asc",
    )


def get_attendance_map(employee_names, from_date, to_date):
    attendance_map = {}

    records = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employee_names],
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": ["<", 2],
        },
        fields=["employee", "attendance_date", "status"],
    )

    for record in records:
        attendance_map[(record.employee, getdate(record.attendance_date))] = get_status_abbr(record.status)

    return attendance_map


def get_holiday_map(employees, company, from_date, to_date):
    holiday_map = {}

    company_holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

    holiday_lists = {
        employee.holiday_list or company_holiday_list
        for employee in employees
        if employee.holiday_list or company_holiday_list
    }

    holiday_rows = []
    if holiday_lists:
        holiday_rows = frappe.get_all(
            "Holiday",
            filters={
                "parent": ["in", list(holiday_lists)],
                "holiday_date": ["between", [from_date, to_date]],
            },
            fields=["parent", "holiday_date", "weekly_off"],
        )

    holiday_index = {}
    for row in holiday_rows:
        holiday_index[(row.parent, getdate(row.holiday_date))] = "WO" if cint(row.weekly_off) else "H"

    for employee in employees:
        holiday_list = employee.holiday_list or company_holiday_list
        if not holiday_list:
            continue

        for holiday_date in daterange(from_date, to_date):
            holiday_status = holiday_index.get((holiday_list, holiday_date))
            if holiday_status:
                holiday_map[(employee.name, holiday_date)] = holiday_status

    return holiday_map


def daterange(from_date, to_date):
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


def get_data(employees, day_columns, attendance_map, holiday_map):
    data = []

    for employee in employees:
        row = {
            "employee": employee.name,
            "employee_name": employee.employee_name,
            "department": employee.department,
            "designation": employee.designation,
            "total_present": 0,
            "total_absent": 0,
            "total_leave": 0,
            "total_half_day": 0,
            "total_weekly_off": 0,
            "total_holiday": 0,
        }

        for day_column in day_columns:
            current_date = day_column["date"]
            status = attendance_map.get((employee.name, current_date))

            if not status:
                status = holiday_map.get((employee.name, current_date), "")

            row[day_column["fieldname"]] = status

            if status == "P":
                row["total_present"] += 1
            elif status == "A":
                row["total_absent"] += 1
            elif status == "L":
                row["total_leave"] += 1
            elif status == "HD":
                row["total_half_day"] += 1
            elif status == "WO":
                row["total_weekly_off"] += 1
            elif status == "H":
                row["total_holiday"] += 1

        data.append(row)

    return data


def get_status_abbr(status):
    if status in STATUS_ABBR:
        return STATUS_ABBR[status]

    if not status:
        return ""

    parts = [part for part in str(status).split() if part]
    if not parts:
        return ""

    return "".join(part[0].upper() for part in parts)
