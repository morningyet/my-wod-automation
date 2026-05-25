import json
import os
import re

BASE_DIR = r"E:\gitee\wod\my-wod-automation\worldview\worldsource"
TOPICS_DIR = os.path.join(BASE_DIR, "topics")
INDEX_FILE = os.path.join(BASE_DIR, "index.json")

# Load existing index
with open(INDEX_FILE, 'r', encoding='utf-8') as f:
    index = json.load(f)
existing_ids = {t['id'] for t in index}

# Scan all .md files for topic references
all_links = {}  # topic_id -> [(source_file, context)]

for topic_dir in os.listdir(TOPICS_DIR):
    topic_path = os.path.join(TOPICS_DIR, topic_dir)
    if not os.path.isdir(topic_path):
        continue
    for md_file in os.listdir(topic_path):
        if not md_file.endswith('.md'):
            continue
        filepath = os.path.join(topic_path, md_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find viewtopic links mentioned in content (URL patterns in text)
        # Look for topic:id patterns or viewtopic.php?id=XXX
        for match in re.finditer(r'topic:(\d+)', content):
            tid = match.group(1)
            if tid not in all_links:
                all_links[tid] = []
            all_links[tid].append((f"{topic_dir}/{md_file}", "topic ref"))

        # Also scan for viewtopic URL patterns in raw content
        for match in re.finditer(r'viewtopic\.php\?id=(\d+)', content):
            tid = match.group(1)
            if tid not in all_links:
                all_links[tid] = []
            all_links[tid].append((f"{topic_dir}/{md_file}", "url pattern"))

# Separate into existing and new
new_links = {}
existing_links = {}
for tid, sources in all_links.items():
    if tid in existing_ids:
        existing_links[tid] = sources
    else:
        new_links[tid] = sources

print(f"Total unique topic IDs found in posts: {len(all_links)}")
print(f"  Already in index: {len(existing_links)}")
print(f"  New (not in index): {len(new_links)}")
print()

if new_links:
    print("=== NEW topic IDs to investigate ===")
    for tid, sources in sorted(new_links.items()):
        print(f"  topic:{tid}")
        for src, ctx in sources[:3]:
            print(f"    <- {src} ({ctx})")
        if len(sources) > 3:
            print(f"    ... and {len(sources)-3} more references")
