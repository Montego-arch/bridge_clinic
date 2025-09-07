frappe.ui.form.on("Purchase Order", {
    before_submit: function(frm) {
        if (!frm.doc.custom_payment_type) {
            frappe.confirm(
                __("You have not selected a Payment Type. Do you want to continue?"),
                function() {
                    // User clicked Yes -> allow submit
                    frm.doc.custom_payment_type = "Non-Prepayment"; 
                    // Default to Non-Prepayment if nothing chosen
                    frm.save().then(() => {
                        frm.submit();
                    });
                },
                function() {
                    // User clicked No or closed dialog -> stop submission
                    frappe.throw(__("Please select a Payment Type before submitting."));
                }
            );
            // Stop immediate submission
            return false;
        }
    }
});
