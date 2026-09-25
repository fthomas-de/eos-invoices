/*
 * Copy recipient, amount and reason of a payment, to paste into the in game
 * transfer. Alliance Auth's clipboard.js bundle does the copying; this only
 * wires it up and confirms it.
 *
 * The confirmation swaps the regular copy icon for the solid check: Font
 * Awesome Free has no regular "check", and "far fa-check" draws nothing.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const clipboard = new ClipboardJS(".eos-invoices-copy");

    clipboard.on("success", (event) => {
        const icon = event.trigger.querySelector("i");
        if (icon) {
            icon.classList.replace("far", "fas");
            icon.classList.replace("fa-copy", "fa-check");
            setTimeout(() => {
                icon.classList.replace("fas", "far");
                icon.classList.replace("fa-check", "fa-copy");
            }, 1500);
        }
        event.clearSelection();
    });

    // as Alliance Auth's SRP page does: the browser refused, say so in the console
    clipboard.on("error", (event) => {
        console.error("eos_invoices: copy failed", event.action, event.trigger);
    });
});
