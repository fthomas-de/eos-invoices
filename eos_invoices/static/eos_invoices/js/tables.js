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
 * stays until a header is clicked. log.js applies the same two markers
 * through its own copy of this lookup - the two files load on different
 * pages and neither is guaranteed to load before the other.
 *
 * The log table is not marked here: it wants the filterDropDown dropdowns
 * over Source and Corporation, which need DataTables' search feature turned
 * on - see log.js.
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

    document.querySelectorAll("table.eos-invoices-sortable").forEach((table) => {
        new DataTable(table, {
            paging: false,
            searching: false,
            info: false,
            order: defaultSort(table),
            columnDefs: [{ targets: "eos-invoices-no-sort", orderable: false }],
        });
    });
});
