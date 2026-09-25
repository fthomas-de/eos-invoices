/*
 * The log page: a sortable table, and the Source/Corporation filter above it.
 *
 * The filter runs on the server, across every page of 100 entries - a filter
 * in the browser (datatables-filterdropdown, used here before) only ever saw
 * the rows of the page it ran on. Changing a choice sends the filter form;
 * the page links keep the filter.
 *
 * Unlike the other sortable tables the log does not default to Corporation
 * then Description: a log reads as a log, newest first, matching the order
 * the query itself already returns. A header click still re-sorts the
 * current page by anything else.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const filter = document.querySelector("#eos-invoices-log-filter");
    if (filter) {
        filter.querySelectorAll("select").forEach((select) => {
            select.addEventListener("change", () => filter.requestSubmit());
        });
    }

    const table = document.querySelector("#eos-invoices-log-table");
    if (!table) {
        return; // an empty log, or an empty filter result, renders no table
    }

    // Alliance Auth's DataTables translation, set by base.html; empty for English
    const holder = document.querySelector("[data-eos-invoices-datatables-language]");
    const languageUrl = holder ? holder.dataset.eosInvoicesDatatablesLanguage : "";

    new DataTable(table, {
        ...(languageUrl ? { language: { url: languageUrl } } : {}),
        paging: false,
        searching: false,
        info: false,
        order: [[0, "desc"]], // Date, newest first
        columnDefs: [{ targets: "eos-invoices-no-sort", orderable: false }],
    });
});
