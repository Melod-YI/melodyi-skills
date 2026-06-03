"""Fetch HackerNews comments by story ID and output trimmed JSON.

Pruning is applied when the comment count exceeds a threshold to keep
the most discussion-worthy comments within a budget.

Usage:
    python fetch_comments.py <story_id>
    python fetch_comments.py <story_id> --verbose
    python fetch_comments.py <story_id> --threshold 50 --budget 30
"""

import argparse
import json
import logging
import sys

import requests

logger = logging.getLogger("hn_fetch")

API_URL = "http://hn.algolia.com/api/v1/items/{id}"

DEFAULT_THRESHOLD = 201
DEFAULT_BUDGET = 200
MAX_SUBTREE_DESCENDANTS = 10


def count_nodes(node: dict) -> int:
    """Count total nodes in the tree including this node."""
    return 1 + sum(count_nodes(c) for c in node.get("children", []))


def count_descendants(node: dict) -> int:
    """Count total descendants of this node (excluding the node itself)."""
    return sum(1 + count_descendants(c) for c in node.get("children", []))


def trim_node(node: dict) -> dict:
    """Recursively trim a HackerNews item node, keeping only author, text, and children.

    Empty children arrays are omitted to reduce noise.
    """
    trimmed = {
        "author": node.get("author"),
        "text": node.get("text"),
    }
    children = node.get("children", [])
    if children:
        trimmed["children"] = [trim_node(child) for child in children]
    return trimmed


def remove_leaves(node: dict) -> int:
    """Remove all leaf nodes (no children) from the subtree. Returns count removed.

    The node itself is never removed (it's the root or a non-leaf parent).
    Nodes that become leaves after inner removals are kept for the next round.
    """
    children = node.get("children", [])
    if not children:
        return 0

    removed = 0
    remaining = []
    for child in children:
        if not child.get("children", []):
            removed += 1
        else:
            inner_removed = remove_leaves(child)
            removed += inner_removed
            # Clean up children key if child became a leaf from inner removals
            if not child.get("children", []):
                child.pop("children", None)
            remaining.append(child)

    if remaining:
        node["children"] = remaining
    else:
        node.pop("children", None)

    return removed


def prune_tree(root: dict, threshold: int, budget: int) -> dict:
    """Prune the comment tree to stay within budget when total exceeds threshold.

    Phase 1 — subtree removal: remove entire top-level threads one at a time,
    always picking the one with fewest descendants. Stop when the smallest
    remaining thread has > MAX_SUBTREE_DESCENDANTS descendants, or budget is met.

    Phase 2 — leaf pruning: iteratively remove all leaf nodes per round
    until budget is met.
    """
    total = count_nodes(root)
    if total <= threshold:
        logger.info("Total %d nodes <= threshold %d, no pruning needed", total, threshold)
        return root

    logger.info("Total %d nodes > threshold %d, pruning to budget %d", total, threshold, budget)

    # Phase 1: Remove low-engagement top-level subtrees one at a time
    # Only remove a subtree if it won't drop us below budget — otherwise
    # let phase 2 handle the remaining nodes more precisely via leaf pruning.
    phase1_removed = 0
    while count_nodes(root) > budget:
        children = root.get("children", [])
        if not children:
            break

        best_idx = min(range(len(children)),
                       key=lambda i: count_descendants(children[i]))
        best_desc = count_descendants(children[best_idx])
        removed_nodes = 1 + best_desc
        nodes_after = count_nodes(root) - removed_nodes

        if best_desc > MAX_SUBTREE_DESCENDANTS:
            logger.info("Phase 1: smallest subtree has %d descendants (> %d limit), "
                        "switching to leaf pruning", best_desc, MAX_SUBTREE_DESCENDANTS)
            break

        if nodes_after < budget:
            logger.info("Phase 1: removing subtree (%d nodes) would drop to %d < budget %d, "
                        "switching to leaf pruning", removed_nodes, nodes_after, budget)
            break

        removed = children.pop(best_idx)
        phase1_removed += removed_nodes
        logger.info("Phase 1: removed subtree by '%s' (%d descendants, %d nodes)",
                    removed.get("author", "?"), best_desc, removed_nodes)

        if not children:
            root.pop("children", None)
            break

    # Phase 2: Iterative leaf pruning
    phase2_removed = 0
    round_num = 0
    while count_nodes(root) > budget:
        round_num += 1
        removed = remove_leaves(root)
        if removed == 0:
            break
        phase2_removed += removed
        logger.info("Phase 2 round %d: removed %d leaves, remaining %d nodes",
                    round_num, removed, count_nodes(root))

    logger.info("Pruning complete: removed %d nodes (phase1=%d, phase2=%d), remaining %d",
                phase1_removed + phase2_removed, phase1_removed, phase2_removed, count_nodes(root))

    return root


def fetch_comments(story_id: int, threshold: int, budget: int) -> dict:
    """Fetch HackerNews story/comments by ID and return trimmed + pruned structure."""
    url = API_URL.format(id=story_id)
    logger.info("Fetching HackerNews item id=%s from %s", story_id, url)

    resp = requests.get(url, timeout=30)
    logger.info("Response status: %s", resp.status_code)

    if resp.status_code != 200:
        logger.error("Request failed with status %s: %s", resp.status_code, resp.text[:200])
        print(f"Error: API request failed with status {resp.status_code}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    logger.info("Raw response received, root author=%s, children count=%s",
                data.get("author"), len(data.get("children", [])))

    result = trim_node(data)
    logger.info("Trimmed structure built, %d nodes", count_nodes(result))

    result = prune_tree(result, threshold, budget)
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch HackerNews comments and output trimmed JSON")
    parser.add_argument("story_id", type=int, help="HackerNews story ID")
    parser.add_argument("--verbose", action="store_true", help="Enable diagnostic logs on stderr")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help=f"Node count threshold to trigger pruning (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                        help=f"Target node count after pruning (default: {DEFAULT_BUDGET})")
    args = parser.parse_args()

    if args.threshold <= args.budget:
        print("Error: threshold must be greater than budget", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    result = fetch_comments(args.story_id, args.threshold, args.budget)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()