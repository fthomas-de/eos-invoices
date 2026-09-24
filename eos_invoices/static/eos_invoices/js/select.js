/*
 * Row selection on the admin overview.
 *
 * A box marked data-eos-invoices-select-all ticks every row box whose
 * data-group matches its value; the value "all" ticks every row on the page,
 * across Corporations. The button marked data-eos-invoices-selected-count
 * shows how many rows are ticked and stays disabled while there are none.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const rows = [...document.querySelectorAll("input.eos-invoices-row")];
    const toggles = [...document.querySelectorAll("input[data-eos-invoices-select-all]")];
    const button = document.querySelector("[data-eos-invoices-selected-count]");
    if (!rows.length || !button) {
        return;
    }
    const counter = button.querySelector(".eos-invoices-count");

    const members = (toggle) => {
        const group = toggle.dataset.eosInvoicesSelectAll;
        return group === "all" ? rows : rows.filter((row) => row.dataset.group === group);
    };

    const refresh = () => {
        const ticked = rows.filter((row) => row.checked).length;
        counter.textContent = ticked;
        button.disabled = ticked === 0;

        // a group box shows all, none or some of its rows
        toggles.forEach((toggle) => {
            const own = members(toggle);
            const on = own.filter((row) => row.checked).length;
            toggle.checked = on > 0 && on === own.length;
            toggle.indeterminate = on > 0 && on < own.length;
        });
    };

    toggles.forEach((toggle) => {
        toggle.addEventListener("change", () => {
            members(toggle).forEach((row) => {
                row.checked = toggle.checked;
            });
            refresh();
        });
    });
    rows.forEach((row) => row.addEventListener("change", refresh));

    refresh();
});
