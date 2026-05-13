frappe.pages['playbook-builder'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: 'Playbook Builder',
      single_column: true
    });
  
    $(page.body).html(`<h1>🔥 Playbook Builder Working</h1>`);
  };