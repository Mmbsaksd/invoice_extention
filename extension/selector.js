function selectorLogic(args) {
    const [labelText, expectedType] = args;
    const normalize = (val) => (val || "").toString().toLowerCase().replace(/[\.\:\#\*]/g, '').trim();
    const target = normalize(labelText);
    const doc = document;

    const getTxt = (el) => normalize(el.innerText || el.textContent);
    const inputs = Array.from(doc.querySelectorAll('input:not([type="hidden"]), textarea, [role="textbox"]'));

    // Helper: Precise alignment check
    const isAligned = (lRect, iRect) => {
        const vCenterDist = Math.abs((lRect.top + lRect.height / 2) - (iRect.top + iRect.height / 2));
        const horizontalDist = iRect.left - lRect.right;
        // Aligned if vertical centers are close AND input is to the right (within 400px)
        return vCenterDist < 15 && horizontalDist > -10 && horizontalDist < 400;
    };

    // 1. Direct attribute match (high confidence)
    for (const input of inputs) {
        const attr = normalize(input.id + input.name + input.placeholder + (input.getAttribute('aria-label') || ""));
        if (target && attr.includes(target)) return { status: 'OK', element: input };
    }

    // 2. Label/Text proximity search with alignment validation
    const labels = Array.from(doc.querySelectorAll('label, span, div, td, b')).filter(el => {
        const text = getTxt(el);
        return text === target || (text.includes(target) && text.length < 30);
    });

    for (const lEl of labels) {
        const lRect = lEl.getBoundingClientRect();
        if (lRect.width === 0) continue;

        // Search inputs in proximity
        const nearbyInputs = inputs.filter(input => {
            const iRect = input.getBoundingClientRect();
            return isAligned(lRect, iRect);
        }).sort((a, b) => {
            const aRect = a.getBoundingClientRect();
            const bRect = b.getBoundingClientRect();
            return (aRect.left - lRect.right) - (bRect.left - lRect.right);
        });

        if (nearbyInputs.length > 0) {
            console.log(`Invoice Assistant: Aligned input found for '${labelText}'`);
            return { status: 'OK', element: nearbyInputs[0] };
        }

        // Fallback: Check parent's scope for specific SAP table cells
        let ancestor = lEl.closest('tr, .sapUiTableTr, .sapMListTblRow, .sapW_GridRow');
        if (ancestor) {
            let input = ancestor.querySelector('input:not([type="hidden"]), textarea');
            if (input) return { status: 'OK', element: input };
        }
    }

    return { status: 'NOT_FOUND' };
}
