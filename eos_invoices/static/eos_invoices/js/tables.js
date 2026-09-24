/*
 * Sortable tables: every table marked eos-invoices-sortable.
 *
 * Sorting only - no paging, no search box. Paging would take rows out of the
 * page, and a ticked box on a hidden page would not be sent with the form.
 * Cells sort by their data-order where they have one, so "1.500.000 ISK"
 * sorts as a number. The server's order stays until a header is clicked.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    document.querySelectorAll("table.eos-invoices-sortable").forEach((table) => {
        new DataTable(table, {
            paging: false,
            searching: false,
            info: false,
            order: [],
            columnDefs: [{ targets: "eos-invoices-no-sort", orderable: false }],
        });
    });
});
