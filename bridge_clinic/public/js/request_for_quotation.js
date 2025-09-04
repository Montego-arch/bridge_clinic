frappe.ui.form.on("Request for Quotation", {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Purchase Order",
                    filters: {
                        custom_linked_rfq: frm.doc.name   // ✅ use custom field only
                    },
                    fields: ["name"],
                    limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let po_name = r.message[0].name;
                        frm.add_custom_button(
                            __("View Purchase Order"),
                            function() {
                                frappe.set_route("Form", "Purchase Order", po_name);
                            }
                        );
                    }
                }
            });
        }
    }
});


