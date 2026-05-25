(() => {
const posts = [];
const tables = document.querySelectorAll('table');

for (const table of tables) {
    const text = table.textContent || '';
    if (!text.includes('[post:')) continue;

    const rows = table.querySelectorAll('tr');
    if (rows.length < 2) continue;

    const row0 = rows[0];
    const tds0 = row0.querySelectorAll('td');
    if (tds0.length < 2) continue;

    const authorTd = tds0[0];
    const contentTd = tds0[1];

    // Author name
    const authorLink = authorTd.querySelector('a');
    const authorName = authorLink?.textContent?.trim() || '';

    // Post id
    const postMatch = authorTd.textContent?.match(/\[post:(\d+)\]/);
    const postId = postMatch ? postMatch[1] : '';
    if (!postId) continue;

    // Date from row1
    const row1 = rows[1];
    const dateTd = row1?.querySelector('td');
    const dateMatch = dateTd?.textContent?.match(/(\d{4}\u5e74\d{1,2}\u6708\d{1,2}\u65e5[\s\d:]+)/);
    const dateText = dateMatch ? dateMatch[1]?.trim() : '';

    // Content - get inner divs if available, otherwise full text
    let content = '';
    const innerDivs = contentTd.querySelectorAll(':scope > div');
    if (innerDivs.length > 0) {
        const parts = [];
        for (const d of innerDivs) {
            const t = d.innerText?.trim();
            if (t) parts.push(t);
        }
        content = parts.join('\n\n');
    } else {
        content = contentTd.innerText?.trim() || '';
    }

    // Remove "last edited" suffix
    const editMarker = '\u6700\u540e\u7f16\u8f91';
    const editIdx = content.lastIndexOf(editMarker);
    if (editIdx > 0) {
        content = content.substring(0, editIdx).trim();
    }

    // Collect viewtopic links from content
    const links = [];
    const linkEls = contentTd.querySelectorAll('a[href*="viewtopic.php?id="]');
    for (const a of linkEls) {
        const m = a.href?.match(/viewtopic\.php\?id=(\d+)/);
        if (m) {
            links.push({ topicId: m[1], text: a.textContent?.trim() || '' });
        }
    }

    posts.push({ postId, author: authorName, date: dateText, content, links });
}

return JSON.stringify(posts);
})()
