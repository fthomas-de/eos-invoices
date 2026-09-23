/* Ask before a form marked eos-invoices-confirm is sent, e.g. deleting a source. */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    document.querySelectorAll("form.eos-invoices-confirm").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.question)) {
                event.preventDefault();
            }
        });
    });
});
