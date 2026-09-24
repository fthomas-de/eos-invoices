/*
 * The log table: sortable like the others, plus AA's own filterDropDown
 * above the Source and Corporation columns - the two a long log actually has
 * few repeating values for, the same way groupmanagement filters by
 * Corporation and Group.
 *
 * Unlike the other sortable tables it does not default to Corporation then
 * Description: a log reads as a log, newest first, matching the order the
 * query itself already returns across every page - not the Corporation/
 * Description grouping tables.js uses elsewhere. A header click still
 * re-sorts the current page by anything else.
 *
 * filterDropDown reads each column's search through DataTables' own search
 * feature, so unlike tables.js this table cannot set searching: false.
 * Labels are translated server side and travel as data - a static file
 * cannot read the catalogue.
 *
 * Option names are camelCase (labelFilter, labelDropdownAll) - this is
 * ppfeufer's datatables-filterdropdown (bundled by Alliance Auth as
 * bundles/filterdropdown-js.html), not the older snake_case filterDropDown.js
 * a plain look at Alliance Auth's own git checkout would suggest; the venv's
 * installed version is the one that actually renders.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const table = document.querySelector("#eos-invoices-log-table");
    if (!table) {
        return; // the empty state renders no table at all
    }

    const labels = JSON.parse(document.getElementById("eos-invoices-log-labels").textContent);

    new DataTable(table, {
        paging: false,
        info: false,
        order: [[0, "desc"]], // Date, newest first
        columnDefs: [{ targets: "eos-invoices-no-sort", orderable: false }],
        filterDropDown: {
            labelFilter: labels.filterLabel,
            columns: [
                { idx: 2, labelDropdownAll: labels.allSources },
                { idx: 3, labelDropdownAll: labels.allCorporations },
            ],
        },
    });
});
