// frappe.ui.form.on("Supplier Quotation", {
//     refresh: function(frm) {
//         if (!frm.is_new()) {
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Purchase Order Item",
//                     filters: { supplier_quotation: frm.doc.name },  // check actual fieldname in PO Item
//                     fields: ["parent"]
//                 },
//                 callback: function(r) {
//                     if (r.message && r.message.length) {
//                         // get unique parent POs
//                         let po_names = [...new Set(r.message.map(i => i.parent))];

//                         po_names.forEach(function(po) {
//                             frm.add_custom_button(
//                                 __("View PO: " + po),
//                                 function() {
//                                     frappe.set_route("Form", "Purchase Order", po);
//                                 },
//                                 __("Purchase Orders") // optional group
//                             );
//                         });
//                     }
//                 }
//             });
//         }
//     }
// });

