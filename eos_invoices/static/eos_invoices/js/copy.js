/* Copy recipient, amount and reason of a payment, to paste into the in game transfer. */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const clipboard = new ClipboardJS(".eos-invoices-copy");

    clipboard.on("success", (event) => {
        const icon = event.trigger.querySelector("i");
        icon.classList.replace("fa-copy", "fa-check");
        setTimeout(() => icon.classList.replace("fa-check", "fa-copy"), 1500);
        event.clearSelection();
    });
});
