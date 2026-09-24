/*
 * Ask before a form marked eos-invoices-confirm is sent, e.g. deleting a
 * source. A form with several submit buttons can give each its own question:
 * the clicked button's data-question wins over the form's.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    document.querySelectorAll("form.eos-invoices-confirm").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const question = event.submitter?.dataset.question || form.dataset.question;
            if (question && !window.confirm(question)) {
                event.preventDefault();
            }
        });
    });
});
