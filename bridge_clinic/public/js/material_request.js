frappe.ui.form.on("Material Request", {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            frappe.db.get_value("Request for Quotation", {
                linked_mr: frm.doc.name
            }, "name").then(r => {
                if (r.message && r.message.name) {
                    frm.add_custom_button(
                        __("View Request for Quotation"),
                        function() {
                            frappe.set_route("Form", "Request for Quotation", r.message.name);
                        }
                    );
                }
            });
        }
    }
});
