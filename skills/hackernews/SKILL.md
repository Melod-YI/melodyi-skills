---
name: hackernews
description: Search Hacker News for articles by URL and fetch/prune comment threads. Use this skill whenever the user wants to find HN discussions for a specific article URL, retrieve comments from an HN story, analyze HN community reactions, summarize or review Hacker News comment threads, or check if a URL has been discussed on HN. Also trigger when the user mentions "Hacker News", "HN comments", "HN discussion", or asks about community feedback on a tech article, even if they don't explicitly ask for a "search" or "fetch" operation.
---

# Hacker News Search & Comment Fetcher

Two CLI tools for interacting with Hacker News via the Algolia HN Search API:

1. **search_hn.py** — Find HN discussions by article URL
2. **fetch_comments.py** — Fetch and intelligently prune comment trees

## Scripts

### scripts/search_hn.py

Search for an HN story matching a given URL.

**Usage:**
```bash
python scripts/search_hn.py <url>
python scripts/search_hn.py <url> --verbose
```

**How it works:**
- Queries the Algolia HN Search API with `restrictSearchableAttributes=url` to find stories
- Normalizes URLs before comparison: strips protocol, `www.` prefix, trailing slashes; lowercases hostname; preserves path case
- Outputs the HN discussion URL (e.g., `https://news.ycombinator.com/item?id=12345`) on match
- Outputs `无匹配` when no match is found

**Exit codes:** 0 on success (match or no match), 1 on API errors (including 429 rate limit).

**When to use:** When you have an article URL and want to know if it was discussed on HN, or when you need the story ID to fetch comments.

### scripts/fetch_comments.py

Fetch the full comment tree for an HN story and output trimmed JSON.

**Usage:**
```bash
python scripts/fetch_comments.py <story_id>
python scripts/fetch_comments.py <story_id> --verbose
python scripts/fetch_comments.py <story_id> --threshold 50 --budget 30
```

**Parameters:**
- `story_id` — The HN story ID (numeric, found in the URL: `item?id=XXXXX`)
- `--threshold` — Node count that triggers pruning (default: 201)
- `--budget` — Target max nodes after pruning (default: 200)
- Constraint: threshold must be greater than budget

**How it works:**
- Fetches the complete comment tree via `http://hn.algolia.com/api/v1/items/{id}`
- Trims each node to only `author`, `text`, and `children` (discarding timestamps, IDs, points, etc.)
- When total nodes exceed threshold, applies two-phase pruning to fit within budget:
  - **Phase 1 (subtree removal):** Removes entire top-level threads one at a time, starting with the smallest/least-engaged threads (fewest descendants). Stops when the smallest remaining thread has >10 descendants, or when removing the next subtree would drop below budget.
  - **Phase 2 (leaf pruning):** Iteratively strips all leaf nodes (comments with no replies) round by round until the tree is within budget.
- Outputs clean JSON to stdout; diagnostic logs go to stderr with `--verbose`

**Why pruning matters:** HN threads can have thousands of comments. The pruning algorithm preserves the most discussion-rich threads while staying within a manageable size — ideal for feeding into an LLM context window or getting a quick overview of the discussion.

## Typical Workflow

### Find and read comments for an article

```bash
# Step 1: Search for the HN discussion
HN_URL=$(python scripts/search_hn.py "https://example.com/article")

if [ "$HN_URL" != "无匹配" ]; then
    # Extract story ID from URL (e.g., "item?id=12345" → 12345)
    STORY_ID=$(echo "$HN_URL" | grep -oP 'id=\K\d+')

    # Step 2: Fetch comments (pruning applied if > 200 nodes)
    python scripts/fetch_comments.py "$STORY_ID"
fi
```

### Handling large discussions

For popular articles with many comments, adjust threshold and budget:

```bash
# More aggressive pruning — keep only the top ~50 comments
python scripts/fetch_comments.py 12345 --threshold 51 --budget 50

# Relaxed — allow up to 500 comments
python scripts/fetch_comments.py 12345 --threshold 501 --budget 500
```

### One-liner with verbose logging

```bash
python scripts/search_hn.py "https://example.com/article" --verbose 2>&1 | tee search.log
python scripts/fetch_comments.py 12345 --verbose 2>fetch.log | jq .
```

## Output Formats

### search_hn.py
- **Match found:** prints the HN discussion URL, one line, e.g. `https://news.ycombinator.com/item?id=48318313`
- **No match:** prints `无匹配`

### fetch_comments.py
Outputs a JSON tree. Each node has only:
```json
{
  "author": "username",
  "text": "<p>HTML comment text</p>",
  "children": [ ... ]
}
```
- `children` is omitted for leaf nodes (no replies)
- `text` can be `null` for the story root node
- Comment `text` contains HTML as returned by HN

## Dependencies

- Python 3.10+
- `requests` library (`pip install requests`)

## Testing

Run the full test suite from the project root:

```bash
pip install requests pytest requests-mock
pytest test_search_hn.py test_fetch_comments.py -v
```

## Example Data

- `demo.json` — Small sample (story 48318313, ~15 nodes) for basic testing
- `demo2.json` — Large sample for stress testing the pruning algorithm
