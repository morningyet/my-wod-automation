import json
import os
import re
import subprocess
import time
import sys

BASE_DIR = r"E:\gitee\wod\my-wod-automation\worldview\worldsource"
TOPICS_DIR = os.path.join(BASE_DIR, "topics")
EXTRACT_JS = os.path.join(BASE_DIR, "extract_posts.js")
INDEX_FILE = os.path.join(BASE_DIR, "index.json")
# Use node directly to call playwright-cli
import shutil

NODE_PATH = shutil.which('node')
PW_JS = r"F:\Program Files\nodejs\node_modules\@playwright\cli\playwright-cli.js"

def _pw_args(extra_args):
    """Build playwright-cli args."""
    return [NODE_PATH, PW_JS] + extra_args

def run_playwright_eval_file(js_file):
    """Run playwright-cli run-code from file."""
    result = subprocess.run(
        _pw_args(['--s=default', 'run-code', f'--filename={js_file}']),
        capture_output=True, timeout=30,
        text=True, encoding='utf-8', errors='replace'
    )
    return result.stdout.strip()

def run_playwright_eval(js_code):
    """Run playwright-cli eval."""
    result = subprocess.run(
        _pw_args(['--s=default', '--raw', 'eval', js_code]),
        capture_output=True, timeout=30,
        text=True, encoding='utf-8', errors='replace'
    )
    return result.stdout.strip()

def run_playwright_cmd(cmd):
    """Run a playwright-cli command."""
    result = subprocess.run(
        _pw_args(['--s=default'] + cmd),
        capture_output=True, timeout=30,
        text=True, encoding='utf-8', errors='replace'
    )
    return result.stdout

def sanitize_folder_name(name):
    """Create a safe folder name from topic title."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()[:80]
    return name

def save_post_as_md(topic_title, post, topic_dir):
    """Save a single post as a markdown file."""
    post_id = post['postId']
    filepath = os.path.join(topic_dir, f"{post_id}.md")

    lines = [
        f"# {topic_title}",
        "",
        f"- 链接: [post:{post_id}]",
        f"- 作者: {post['author']}",
        f"- 日期: {post['date']}",
        "",
        "## 正文",
        "",
        post['content'],
    ]

    if post.get('links'):
        lines.append("")
        lines.append("## 帖内链接")
        for link in post['links']:
            lines.append(f"- [{link['text']}](topic:{link['topicId']})")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return filepath

def crawl_topic(topic):
    """Crawl a single topic, handling multi-page posts."""
    topic_id = topic['id']
    title = topic['title']
    folder_name = sanitize_folder_name(f"{topic_id}_{title}")
    topic_dir = os.path.join(TOPICS_DIR, folder_name)
    os.makedirs(topic_dir, exist_ok=True)

    session_hero_id = "212647"
    base_url = f"https://delta.world-of-dungeons.org/wod/spiel/forum/viewtopic.php?id={topic_id}&board=kein&session_hero_id={session_hero_id}"

    # Write a per-topic JS file that navigates and extracts
    all_posts = []
    page_num = 1
    max_pages = 20

    while page_num <= max_pages:
        url = base_url if page_num == 1 else f"{base_url}&p={page_num}"
        print(f"  Page {page_num}: {url}")

        run_playwright_cmd(['goto', url])
        time.sleep(1.5)

        # Use --raw eval with the extraction script
        # Read JS, pass inline
        with open(EXTRACT_JS, 'r', encoding='utf-8') as f:
            js_code = f.read().strip()

        result = run_playwright_eval(js_code)
        try:
            parsed = json.loads(result)
            # --raw eval returns double-encoded JSON string
            if isinstance(parsed, str):
                posts = json.loads(parsed)
            else:
                posts = parsed
        except json.JSONDecodeError:
            print(f"  WARNING: Failed to parse for page {page_num}: {result[:200]}")
            break

        if not posts:
            break

        all_posts.extend(posts)

        # Check for next page
        pagination_result = run_playwright_eval(
            "JSON.stringify([...document.querySelectorAll('a')].filter(a=>a.textContent?.trim()?.match(/^\\d+$/)&&a.href?.includes('p=')).map(a=>a.textContent.trim()))"
        )
        try:
            parsed = json.loads(pagination_result)
            page_links = json.loads(parsed) if isinstance(parsed, str) else parsed
            next_page = page_num + 1
            if str(next_page) in page_links:
                page_num = next_page
            else:
                break
        except:
            break

    # Save all posts
    saved = 0
    for post in all_posts:
        path = save_post_as_md(title, post, topic_dir)
        saved += 1

    return saved, len(all_posts), topic_dir

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        topics = json.load(f)

    batch = topics[offset:offset+limit]
    print(f"Crawling {len(batch)} topics (offset={offset}, limit={limit})")

    for i, topic in enumerate(batch):
        idx = offset + i + 1
        print(f"\n[{idx}/{len(topics)}] {topic['title']} (id={topic['id']}, replies={topic['replies']})")
        try:
            saved, total, topic_dir = crawl_topic(topic)
            print(f"  -> Saved {saved} posts to {topic_dir}")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone! Crawled {len(batch)} topics.")

if __name__ == '__main__':
    main()
