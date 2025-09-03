frappe.ui.form.on("Expense Claim", {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Payment Request",
                    filters: {
                        reference_doctype: "Expense Claim",
                        reference_name: frm.doc.name
                    },
                    fields: ["name"]
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let pr_name = r.message[0].name;
                        frm.add_custom_button(
                            __("View Payment Request"),
                            function() {
                                frappe.set_route("Form", "Payment Request", pr_name);
                            },
                            __("Payments")
                        );
                    }
                }
            });
        }
    }
});
