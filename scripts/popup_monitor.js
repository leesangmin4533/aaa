(() => {
    // Check if the script is already injected
    if (window.popupMonitor) {
        console.log("[PopupMonitor] Monitor is already running.");
        return;
    }

    console.log("[PopupMonitor] Initializing...");

    // Store logs to be retrieved by Python
    window.popupMonitorLogs = [];
    const log = (message) => {
        console.log(`[PopupMonitor] ${message}`);
        window.popupMonitorLogs.push(`[${new Date().toISOString()}] ${message}`);
    };

    const closePopup = (node) => {
        // Ensure it's an element node before proceeding
        if (node.nodeType !== 1) {
            return false;
        }

        log(`Checking node for popup: ${node.tagName}#${node.id}.${node.className}`);

        const textSelectors = ['닫기', '확인', '취소', 'Close', 'OK', 'Cancel', '×', 'X'];
        const idSelectors = [
            'btn_topClose', 'btnClose',
            'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_close',
            'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_closeTop',
            'mainframe.HFrameSet00.VFrameSet00.TopFrame.STZZ210_P0.form.btn_enter'
        ];
        const classSelectors = ['close', 'popup-close', 'btn_pop_close'];

        const elementsToSearch = new Set([node, ...node.querySelectorAll('button, a, div')]);

        for (const el of elementsToSearch) {
            if (!el || el.offsetParent === null) continue;

            const elIdentifier = `${el.tagName}#${el.id}.${el.className}`;

            if (idSelectors.includes(el.id)) {
                log(`Found close button by ID: ${el.id}. Clicking...`);
                el.click();
                return true;
            }
            for (const cls of classSelectors) {
                if (el.classList.contains(cls)) {
                    log(`Found close button by Class: ${cls} on element ${elIdentifier}. Clicking...`);
                    el.click();
                    return true;
                }
            }
            for (const text of textSelectors) {
                if (el.innerText && el.innerText.trim() === text) {
                    log(`Found close button by Text: "${text}" on element ${elIdentifier}. Clicking...`);
                    el.click();
                    return true;
                }
            }
        }
        return false;
    };

    const callback = (mutationsList, observer) => {
        log(`MutationObserver triggered. Found ${mutationsList.length} mutations.`);
        for (const mutation of mutationsList) {
            log(`- Mutation type: ${mutation.type}. Attribute: ${mutation.attributeName || 'N/A'}`);
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(node => {
                    log(`Node added: ${node.nodeName}`);
                    closePopup(node);
                });
            } else if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                log(`Style attribute changed on: ${mutation.target.tagName}`);
                const style = window.getComputedStyle(mutation.target);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    closePopup(mutation.target);
                }
            }
        }
    };

    const startMonitor = () => {
        if (window.popupMonitor?.observer) {
            log("Monitor already started.");
            return;
        }
        const targetNode = document.body;
        const config = { attributes: true, childList: true, subtree: true, attributeFilter: ['style'] };
        const observer = new MutationObserver(callback);
        observer.observe(targetNode, config);

        window.popupMonitor = { observer: observer };
        log("Popup monitor started successfully.");

        log("Performing initial scan for existing popups...");
        document.querySelectorAll('div').forEach(node => {
            const style = window.getComputedStyle(node);
            if (style.display !== 'none' && style.visibility !== 'hidden' && (node.className.includes('pop') || node.id.includes('pop'))) {
                closePopup(node);
            }
        });
        log("Initial scan complete.");
    };

    window.popupTools = { startMonitor: startMonitor };

})();