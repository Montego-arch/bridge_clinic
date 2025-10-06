frappe.ui.form.on('Expense Claim Detail', {
    custom_rate(frm, cdt, cdn) {
        calculate_amount_and_total(frm, cdt, cdn);
    },
    custom_quantity(frm, cdt, cdn) {
        calculate_amount_and_total(frm, cdt, cdn);
    },
    amount(frm, cdt, cdn) {
        update_total_sanctioned_amount(frm);
    }
});

function calculate_amount_and_total(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    let rate = flt(row.custom_rate || 0);
    let qty = flt(row.custom_quantity || 0);

    let total = rate * qty;

    frappe.model.set_value(cdt, cdn, 'amount', total);
    update_total_sanctioned_amount(frm);
}

function update_total_sanctioned_amount(frm) {
    let total = 0;
    (frm.doc.expenses || []).forEach(row => {
        total += flt(row.amount || 0);
    });

    frm.set_value('total_sanctioned_amount', total);
    frm.refresh_field('total_sanctioned_amount');
}
