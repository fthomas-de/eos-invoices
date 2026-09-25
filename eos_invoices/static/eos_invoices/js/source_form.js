/*
 * Field dropdowns and placeholder chips of the payment source form.
 *
 * The server renders the dropdowns for the model already chosen. This only
 * refills them when the model or the paid mode changes, and offers the fields
 * as placeholders for the reason and description templates. The server checks
 * everything again on save, so nothing here has to be trusted.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const form = document.getElementById("eos-invoices-source-form");
    if (!form) {
        return;
    }

    const kinds = JSON.parse(document.getElementById("eos-invoices-accepted-kinds").textContent);
    let options = JSON.parse(document.getElementById("eos-invoices-field-options").textContent);

    const modelSelect = form.querySelector("[name=model_label]");
    const paidMode = form.querySelector("[name=paid_mode]");
    const pathSelects = form.querySelectorAll("select[data-eos-invoices-path]");

    const acceptedFor = (name) => {
        if (name === "paid_field" && paidMode.value === "true") {
            return kinds.paid_field_true;
        }
        return kinds[name] || null;
    };

    const fillSelect = (select) => {
        const accepted = acceptedFor(select.dataset.eosInvoicesPath);
        const current = select.value;

        select.replaceChildren(new Option("---------", ""));
        options
            .filter((option) => !accepted || accepted.includes(option.kind))
            .forEach((option) => select.add(new Option(option.label, option.path)));

        // keep the choice when it still exists under the new filter
        if ([...select.options].some((option) => option.value === current)) {
            select.value = current;
        }
    };

    const insertPlaceholder = (input, path) => {
        const text = `{${path}}`;
        const start = input.selectionStart ?? input.value.length;
        const end = input.selectionEnd ?? input.value.length;

        input.value = input.value.slice(0, start) + text + input.value.slice(end);
        input.focus();
        input.setSelectionRange(start + text.length, start + text.length);
    };

    const fillChips = () => {
        form.querySelectorAll(".eos-invoices-chips").forEach((container) => {
            const input = document.getElementById(container.dataset.target);

            container.replaceChildren(
                ...options.map((option) => {
                    const chip = document.createElement("button");
                    chip.type = "button";
                    chip.className = "btn btn-sm btn-outline-secondary py-0";
                    chip.textContent = option.path;
                    chip.title = option.label;
                    chip.addEventListener("click", () => insertPlaceholder(input, option.path));
                    return chip;
                })
            );
        });
    };

    // counts model changes, so an answer that arrives after a newer request
    // was sent cannot overwrite the fields of the model chosen since
    let request = 0;

    modelSelect.addEventListener("change", async () => {
        const own = ++request;
        let fields = [];
        if (modelSelect.value) {
            const url = `${form.dataset.fieldsUrl}?model=${encodeURIComponent(modelSelect.value)}`;
            try {
                const response = await fetch(url, { headers: { Accept: "application/json" } });
                if (response.ok) {
                    fields = (await response.json()).fields;
                }
            } catch (error) {
                // offline or not JSON: empty dropdowns rather than the old
                // model's fields; the server checks everything on save anyway
                console.error("eos_invoices: loading the fields failed", error);
            }
        }
        if (own !== request) {
            return;
        }
        options = fields;
        pathSelects.forEach(fillSelect);
        fillChips();
    });

    paidMode.addEventListener("change", () => {
        fillSelect(form.querySelector("select[data-eos-invoices-path=paid_field]"));
    });

    fillChips();
});
