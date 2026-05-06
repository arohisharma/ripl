frappe.ui.form.on("Circular", {
    generate_ai_summary(frm) {
        if (!frm.doc.circular_url) {
            frappe.msgprint("Please add Circular URL first");
            return;
        }

        frappe.call({
            method: "ripl.api.circular.enqueue_ai_generation",
            args: {
                name: frm.doc.name
            },
            freeze: false,
            freeze_message: "Processing PDF..."
        }).then(() => {
            frappe.msgprint("AI processing started in background");
        });
    }
});