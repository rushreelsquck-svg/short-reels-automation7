"""
generate_case.py
Generates a fully original true-crime case narration — a respectful,
factual retelling of a CLOSED, well-documented case, broken into
chronological story beats (setup, the crime, the investigation, the
resolution, the legacy). This is not a news-recap channel; it's generative
like the fables/facts/history channels, drawing on well-established public
record rather than reporting on anything still unfolding.

This genre carries real risk if handled carelessly — sensationalizing real
tragedy, naming unconvicted people as guilty, or providing operational
detail about how a crime was carried out. The system prompt below is
deliberately the most restrictive of any channel in this family. Treat any
loosening of these rules as a decision that needs real thought, not a
quick tweak.

Tracks recent cases in state so they don't repeat too often.
"""
import json
import os
import random
from pathlib import Path

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

STATE_SUFFIX = os.environ.get("STATE_SUFFIX", "")
STATE_FILE = Path(__file__).resolve().parent.parent / "state" / f"used_premises{STATE_SUFFIX}.json"

HOOK_STYLES = [
    "If you're seeing this, you need to hear how this case actually ended...",
    "This case took years to solve, and the answer surprised everyone...",
    "No one talks about this case anymore, but they should...",
    "This is the case that changed how investigators do their job...",
    "Here's a case most people have never heard of...",
    "This started as a simple call, and became one of the strangest cases on record...",
    "Investigators almost missed this, until one detail changed everything...",
]

SYSTEM_PROMPT = """You write scripts for a daily YouTube Shorts channel called The Case File,
retelling closed, well-documented true crime cases as respectful, factual narration.

Hard rules — these override any instinct to make the story more dramatic:
- ONLY cover cases that are fully closed with a confirmed legal outcome (conviction, plea, or
  similarly definitive resolution) and are well-documented in extensive public reporting. NEVER
  cover an active/unsolved/ongoing case, and never a case where the legal outcome is unclear.
- NEVER state that someone is guilty of a crime unless they were actually convicted of it. Use
  "convicted," "pleaded guilty," "found guilty" only when that's the documented outcome. If anyone
  other than the convicted party is mentioned, do not imply their guilt.
- NEVER include a case where the victim was a child, or where graphic sexual violence is part of
  the case — skip these entirely and pick a different case instead.
- NO graphic, gratuitous descriptions of violence or suffering. Describe what happened factually
  and briefly; do not dwell on injury detail, gore, or suffering for shock value. The focus is the
  investigation, the human story, and the resolution — not the violence itself.
- NEVER include operational detail about how the crime was carried out beyond what's necessary to
  understand the case — this should never read as a how-to.
- Treat victims with dignity. Center the narration on what happened to them and the pursuit of
  justice, not on sensationalizing their suffering for entertainment.
- Don't include unnecessary personal details (addresses, identifying details of family members,
  etc.) about real private individuals beyond what's essential to the documented case.
- All wording must be entirely original — write your own retelling in your own words. Never lightly
  reskin a specific article, book, or documentary's specific phrasing — the FACTS are public record,
  but the words are always yours.
- Structure as: hook, then 5-7 chronological story beats (setup -> the crime/discovery ->
  investigation -> break in the case -> resolution -> brief legacy/reflection), each 1-2 sentences.
- Open with a hook line in the spirit of the example styles you're given, adapted to fit this case.
- Close with a brief, respectful reflection (not a "follow for more true crime" tone that feels
  flippant given the subject matter) plus a one-line follow nudge.
- Written for narration: short sentences, no headers, no bullet points. Serious, measured tone —
  not breathless or sensationalized.
- For each story beat (not the hook), pick a short visually-literal, NON-graphic stock-footage
  phrase (e.g. "police car lights at night", "courthouse exterior", "detective reviewing files",
  "rain on a window", "old newspaper archive", "evidence folder on a desk") — atmospheric and
  symbolic, never depicting violence, weapons, injury, or anything graphic.
- Call the submit_case_video tool exactly once."""

CASE_TOOL = {
    "name": "submit_case_video",
    "description": "Submit the finished true-crime case video: hook, story beats with visual cues, and upload metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "premise": {"type": "string", "description": "One-sentence summary of which case this is, used only to avoid repeating the same case too often"},
            "title": {"type": "string", "description": "<=95 characters, accurate to the content, serious tone — not sensationalized clickbait"},
            "description": {"type": "string", "description": "2-3 sentences plus a brief, respectful follow nudge"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "8-12 lowercase tags relevant to this case"},
            "hashtags": {"type": "array", "items": {"type": "string"}, "description": "5-8 hashtags starting with #, always include #shorts"},
            "hook": {"type": "string", "description": "The opening hook line, 1 short sentence"},
            "beats": {
                "type": "array",
                "minItems": 5,
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "properties": {
                        "narration": {"type": "string", "description": "1-2 sentences for this story beat"},
                        "visual_query": {"type": "string", "description": "Concrete, non-graphic, atmospheric stock-footage search phrase for this beat"},
                    },
                    "required": ["narration", "visual_query"],
                },
            },
        },
        "required": ["premise", "title", "description", "tags", "hashtags", "hook", "beats"],
    },
}


def _load_used_premises():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return []


def _save_used_premise(premise):
    used = _load_used_premises()
    used.append(premise)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(used[-60:], indent=2))


def generate_case_video() -> dict:
    used_premises = _load_used_premises()
    avoid_text = (
        "Avoid these recently-covered cases — pick a different one:\n" + "\n".join(f"- {p}" for p in used_premises[-20:])
        if used_premises else "No prior cases to avoid yet."
    )
    sample_hooks = "\n".join(f"- {h}" for h in random.sample(HOOK_STYLES, 3))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[CASE_TOOL],
        tool_choice={"type": "tool", "name": "submit_case_video"},
        messages=[{
            "role": "user",
            "content": f"Write today's case video.\n\n{avoid_text}\n\nSome example hook styles for inspiration (adapt, don't recite verbatim):\n{sample_hooks}",
        }],
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    video = dict(tool_use_block.input)

    if not any(h.lower() == "#shorts" for h in video.get("hashtags", [])):
        video.setdefault("hashtags", []).append("#shorts")

    _save_used_premise(video["premise"])
    return video


if __name__ == "__main__":
    print(json.dumps(generate_case_video(), indent=2))
