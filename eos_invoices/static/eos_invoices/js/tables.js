/*
 * Sortable tables: every table marked eos-invoices-sortable.
 *
 * No paging, no search box. Paging would take rows out of the page, and a
 * ticked box on a hidden page would not be sent with the form. Cells sort by
 * their data-order where they have one, so "1.500.000 ISK" sorts as a number.
 *
 * Headers marked eos-invoices-sort-1 and eos-invoices-sort-2 are the initial
 * sort, in that order - Corporation then Description on a table that spans
 * several Corporations, Description alone where there is no Corporation
 * column. Either or both may be absent; without any, the server's own order
 * stays until a header is clicked. A Description cell carries the row's
 * period in data-order, so "01/2027" sorts after "12/2026".
 *
 * The log table is not marked here: it defaults to chronological order
 * rather than this Corporation/Description convention - see log.js.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const defaultSort = (table) => {
        const headers = [...table.querySelectorAll("thead th")];
        return [1, 2]
            .map((level) => headers.findIndex((th) => th.classList.contains(`eos-invoices-sort-${level}`)))
            .filter((index) => index !== -1)
            .map((index) => [index, "asc"]);
    };

    // Alliance Auth's DataTables translation for the viewer's language, set
    // by base.html; empty for English, where DataTables needs none
    const holder = document.querySelector("[data-eos-invoices-datatables-language]");
    const languageUrl = holder ? holder.dataset.eosInvoicesDatatablesLanguage : "";

    document.querySelectorAll("table.eos-invoices-sortable").forEach((table) => {
        new DataTable(table, {
            ...(languageUrl ? { language: { url: languageUrl } } : {}),
            paging: false,
            searching: false,
            info: false,
            order: defaultSort(table),
            columnDefs: [{ targets: "eos-invoices-no-sort", orderable: false }],
        });
    });
});
