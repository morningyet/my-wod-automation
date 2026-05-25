// Scan all viewtopic links within post content areas on the current page
(() => {
    const links = new Set();
    // Find all tables that contain [post:] (these are post content tables)
    const tables = document.querySelectorAll('table');
    for (const table of tables) {
        if (!table.textContent?.includes('[post:')) continue;
        // Find all viewtopic links within this table
        const anchors = table.querySelectorAll('a[href*="viewtopic.php?id="]');
        for (const a of anchors) {
            const m = a.href?.match(/viewtopic\.php\?id=(\d+)/);
            if (m) {
                const tid = m[1];
                const text = a.textContent?.trim() || '';
                // Skip pagination links (just numbers) and navigation
                if (/^\d+$/.test(text)) continue;
                // Skip breadcrumb links (World of Dungeons, etc.)
                if (text.includes('World of Dungeons')) continue;
                if (text.includes('Mentor')) continue;
                if (text.includes('世界之源')) continue;
                links.add(JSON.stringify({ tid, text: text.substring(0, 80) }));
            }
        }
    }
    return JSON.stringify([...links].map(l => JSON.parse(l)));
})()
