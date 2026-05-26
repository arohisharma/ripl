// Copyright (c) 2026, dewansh and contributors
// For license information, please see license.txt

frappe.ui.form.on("Chapter", {
	refresh(frm) {
		setup_chapter_content_image_paste(frm);
	},
});

function setup_chapter_content_image_paste(frm) {
	const field = frm.get_field("content");
	if (!field) return;

	const bind_paste = () => {
		if (!field.quill || field._ripl_paste_bound) return;
		field._ripl_paste_bound = true;

		field.quill.root.addEventListener("paste", (e) => {
			const items = e.clipboardData && e.clipboardData.items;
			if (!items) return;

			for (const item of items) {
				if (item.kind === "file" && item.type.startsWith("image/")) {
					e.preventDefault();
					const file = item.getAsFile();
					if (file) {
						upload_chapter_content_image(frm, file, field.quill);
					}
					return;
				}
			}
		});
	};

	if (field.quill) {
		bind_paste();
		return;
	}

	const original_make_input = field.make_input.bind(field);
	field.make_input = function () {
		original_make_input();
		bind_paste();
	};
}

function upload_chapter_content_image(frm, file, quill) {
	const form_data = new FormData();
	form_data.append("file", file, file.name || "chapter-image.png");
	form_data.append("is_private", "0");
	form_data.append("doctype", frm.doctype);
	form_data.append("docname", frm.docname);
	form_data.append("fieldname", "content");

	frappe.dom.freeze(__("Uploading image..."));

	const xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/method/upload_file", true);
	xhr.setRequestHeader("Accept", "application/json");
	xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);

	xhr.onload = function () {
		frappe.dom.unfreeze();
		if (xhr.status !== 200) {
			frappe.show_alert({
				message: __("Image upload failed"),
				indicator: "red",
			});
			return;
		}

		let response;
		try {
			response = JSON.parse(xhr.responseText);
		} catch (e) {
			frappe.show_alert({
				message: __("Image upload failed"),
				indicator: "red",
			});
			return;
		}

		const file_doc = response.message;
		const file_url = file_doc && (file_doc.file_url || file_doc);
		if (!file_url) return;

		const range = quill.getSelection(true);
		const index = range ? range.index : quill.getLength();
		quill.insertEmbed(index, "image", file_url, "user");
		quill.setSelection(index + 1, 0, "silent");
	};

	xhr.onerror = function () {
		frappe.dom.unfreeze();
		frappe.show_alert({
			message: __("Image upload failed"),
			indicator: "red",
		});
	};

	xhr.send(form_data);
}
