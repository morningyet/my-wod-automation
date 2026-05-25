import json
import os
import subprocess
import time
import sys

BASE_DIR = r"E:\gitee\wod\my-wod-automation\worldview\worldsource"
INDEX_FILE = os.path.join(BASE_DIR, "index.json")
SCAN_JS = os.path.join(BASE_DIR, "scan_page_links.js")
LINKS_FILE = os.path.join(BASE_DIR, "discovered_links.json")

NODE_PATH = "node"
PW_JS = r"F:\Program Files\nodejs\node_modules\@playwright\cli\playwright-cli.js"

def run_pw(args):
    result = subprocess.run(
        [NODE_PATH, PW_JS, '--s=default'] + args,
        capture_output=True, timeout=30,
        text=True, encoding='utf-8', errors='replace'
    )
    return result.stdout

def run_eval(js_code):
    result = subprocess.run(
        [NODE_PATH, PW_JS, '--s=default', '--raw', 'eval', js_code],
        capture_output=True, timeout=30,
        text=True, encoding='utf-8', errors='replace'
    )
    out = result.stdout.strip()
    try:
        parsed = json.loads(out)
        return json.loads(parsed) if isinstance(parsed, str) else parsed
    except:
        return None

def main():
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        topics = json.load(f)

    existing_ids = {t['id'] for t in topics}

    with open(SCAN_JS, 'r', encoding='utf-8') as f:
        scan_js = f.read().strip()

    all_discovered = {}  # topic_id -> {text, found_in: [topic_ids]}

    for i, topic in enumerate(topics):
        tid = topic['id']
        title = topic['title']
        url = f"https://delta.world-of-dungeons.org/wod/spiel/forum/viewtopic.php?id={tid}&board=kein&session_hero_id=212647"

        # Only scan topics with replies (single-post topics won't have internal links usually)
        # But also scan first page of all topics to be thorough
        if i % 20 == 0:
            print(f"[{i+1}/{len(topics)}] Scanning for links...")

        run_pw(['goto', url])
        time.sleep(0.5)

        links = run_eval(scan_js)
        if not links:
            continue

        for link in links:
            link_tid = link['tid']
            link_text = link['text']
            if link_tid == tid:
                continue  # Skip self-reference
            if link_tid not in all_discovered:
                all_discovered[link_tid] = {'text': link_text, 'found_in': [tid]}
            else:
                all_discovered[link_tid]['found_in'].append(tid)

    # Categorize
    new_links = {}
    existing_links = {}
    for link_tid, info in all_discovered.items():
        if link_tid in existing_ids:
            existing_links[link_tid] = info
        else:
            new_links[link_tid] = info

    print(f"\n=== Results ===")
    print(f"Total unique topic IDs referenced in posts: {len(all_discovered)}")
    print(f"  Already in index: {len(existing_links)}")
    print(f"  NEW (not in index): {len(new_links)}")

    # Save results
    results = {
        'existing': existing_links,
        'new': new_links
    }
    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    if new_links:
        print(f"\n=== New topics to investigate ===")
        for tid, info in sorted(new_links.items()):
            sources = ', '.join(set(str(s) for s in info['found_in'][:5]))
            print(f"  topic:{tid} \"{info['text'][:50]}\" (found in: {sources})")

    print(f"\nResults saved to {LINKS_FILE}")

if __name__ == '__main__':
    main()
