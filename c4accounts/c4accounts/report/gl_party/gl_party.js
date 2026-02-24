frappe.query_reports["GL Party"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.year_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.year_end(),
        },
        {
            fieldname: "account",
            label: __("Account"),
            fieldtype: "Link",
            options: "Account",
        },
        {
            fieldname: "voucher_type",
            label: __("Voucher Type"),
            fieldtype: "Select",
            options: "\nJournal Entry\nPayment Entry",
        },
        {
            fieldname: "voucher_no",
            label: __("Voucher No"),
            fieldtype: "Dynamic Link",
            options: "voucher_type",
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Select",
            options: "\nCustomer\nSupplier\nEmployee",
        },
        {
            fieldname: "party",
            label: __("Party"),
            fieldtype: "Dynamic Link",
            options: "party_type",
        },
    ],
};
