"""
youtube_metadata.py
Merges the video's own tags with real YouTube trending keywords for extra
discoverability, then trims everything to YouTube's actual limits.
"""
import re

MAX_TAGS_CHARS = 480
MAX_TITLE_CHARS = 95
MAX_DESCRIPTION_CHARS = 4800


def _sanitize_tag(tag: str) -> str:
    """
    Remove characters YouTube's API rejects in tags.
    The most common culprits are & (from names like "Taylor Swift & Travis Kelce"),
    < and > (from show titles), and " (from quoted phrases in trending keywords).
    Any of these will cause the entire upload to fail with invalidTags.
    """
    tag = re.sub(r'[<>&",]', '', tag)
    tag = ' '.join(tag.split())
    return tag.strip()[:100]


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        clean = _sanitize_tag(item)
        key = clean.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(clean)
    return out


def build_final_metadata(video: dict, trending_keywords: list[str]) -> dict:
    title = video.get("title", "")[:MAX_TITLE_CHARS]

    hashtags = _dedupe_preserve_order(video.get("hashtags", ["#shorts"]))
    hashtag_line = " ".join(hashtags)

    description_parts = [video.get("description", "").strip(), "", hashtag_line]
    description = "\n".join(p for p in description_parts if p)[:MAX_DESCRIPTION_CHARS]

    combined_tags = _dedupe_preserve_order(
        video.get("tags", []) + trending_keywords + ["shorts", "history", "historyfacts", "didyouknow"]
    )

    final_tags = []
    char_budget = MAX_TAGS_CHARS
    for tag in combined_tags:
        if len(tag) + 1 > char_budget:
            break
        final_tags.append(tag)
        char_budget -= len(tag) + 1

    return {"title": title, "description": description, "tags": final_tags}
