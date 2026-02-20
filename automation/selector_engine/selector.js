function selectorLogic(args) {
    const [labelText, expectedType] = args;
    const target = labelText.toLowerCase();
    const doc = document;
    const getTxt = (el) => (el.innerText || el.textContent || "").trim().toLowerCase();
    const inputs = Array.from(doc.querySelectorAll('input:not([type="hidden"]), textarea, [role="textbox"]'));

    for (const input of inputs) {
        const attr = (input.id + input.name + input.placeholder + (input.getAttribute('aria-label') || "")).toLowerCase();
        if (attr.includes(target)) return { status: 'OK', element: input };
    }

    const labels = Array.from(doc.querySelectorAll('label, span, div, td, b')).filter(el => {
        const t = getTxt(el);
        return t === target || (t.includes(target) && t.length < 25);
    });

    for (const lEl of labels) {
        let parent = lEl.parentElement;
        let sib = parent.querySelector('input:not([type="hidden"]), textarea');
        if (sib && sib !== lEl) return { status: 'OK', element: sib };
        let next = parent.nextElementSibling;
        if (next) {
            let nested = next.querySelector('input:not([type="hidden"]), textarea');
            if (nested) return { status: 'OK', element: nested };
        }
        let row = parent.parentElement;
        if (row && (row.tagName === 'TR' || row.classList.contains('sapUiTableTr'))) {
            let nested = row.querySelector('input:not([type="hidden"]), textarea');
            if (nested) return { status: 'OK', element: nested };
        }
    }
    return { status: 'NOT_FOUND' };
}
