"""
generate_case.py
Generates a daily "rare but shocking accidents" video — a factual, respectful
retelling of a real, well-documented accident or disaster that was unusual,
unexpected, and widely discussed because of its bizarre or surprising nature.

Examples of the right content: Great Molasses Flood, Tenerife airport disaster,
Byford Dolphin diving bell accident, Hyatt Regency walkway collapse, Gimli
Glider incident, Bhopal gas tragedy, Chernobyl, Texas City Refinery explosion,
Space Shuttle Challenger. All of these are:
  - Real, confirmed, well-documented events
  - Closed (the event is fully resolved and publicly documented)
  - Interesting because of the unlikely combination of factors that caused them
  - Educational — most led to real safety standard changes

This is not true crime. There are no criminal perpetrators to avoid naming,
no victim privacy concerns of the same kind, and no "guilt before conviction"
problem. The tone is closer to engineering post-mortem or disaster documentary
than crime reporting — curious, analytical, respectful of those who were hurt.

Tracks recent events in state so they don't repeat too often.
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
    "was stranger than any fiction writer would dare invent...",
    "happened because of one decision nobody expected to matter...",
    "changed safety standards around the world overnight...",
    "was caused by something so simple it's almost unbelievable...",
    "happened in seconds and nobody saw it coming...",
    "was the result of a chain of events that each seemed harmless alone...",
    "is still studied by engineers and safety experts today...",
    "had a cause that investigators almost missed entirely...",
]

# High-interest accident/disaster categories and specific known events
HIGH_INTEREST_TOPICS = [
    "aviation accidents", "structural engineering failures", "industrial disasters",
    "chemical plant accidents", "maritime disasters", "bridge collapses",
    "the Tenerife airport disaster", "the Hyatt Regency walkway collapse",
    "the Gimli Glider incident", "the Great Molasses Flood",
    "the Byford Dolphin accident", "the Bhopal gas tragedy",
    "the Space Shuttle Challenger disaster", "the Texas City Refinery explosion",
    "the Chernobyl disaster", "the Deepwater Horizon blowout",
    "the Tacoma Narrows Bridge collapse", "the Three Mile Island accident",
    "nuclear near-misses", "railway disasters", "dam failures",
    "food safety failures", "medical device recalls",
]

SYSTEM_PROMPT = """You write scripts for a daily YouTube Shorts channel called Zero Warning,
telling the stories of real, rare, shocking accidents and disasters — events that were so
unusual, so unexpected, or caused by such a bizarre chain of circumstances that they became
widely studied and discussed, and often changed safety standards forever.

Content scope:
- Real, confirmed, well-documented accidents and disasters (not crimes, not speculation)
- Events that are FULLY resolved and publicly documented — not ongoing or disputed
- The interesting angle: WHY it happened (the unlikely chain of causes), not just WHAT happened
- Events where the cause was surprisingly simple, absurd, or a combination of factors that
  each seemed harmless on their own
- Bonus if the event led to real changes in safety standards, engineering practices, or regulations
- Examples of the right tone: engineering post-mortem, BBC disaster documentary, Smithsonian
  Channel — analytical, curious, respectful of those involved, never exploitative or gloating

Title strategy (important for discovery):
- Lead with the event name or the most striking detail: "The [Event Name]" or a dramatic
  description of what happened. Specific named events outperform generic ones in search.
- Examples of strong titles: "The Day Molasses Flooded Boston at 35mph",
  "Two Planes, One Runway: The Tenerife Disaster", "How a Unit Error Nearly Crashed a 767"
- Follow with why it's fascinating, not just that it happened

Hard rules:
- Every fact must be accurate and based on well-documented public record. Never invent,
  exaggerate, or speculate beyond what's documented. If uncertain, don't include the detail.
- Treat victims and those involved with dignity — this is educational storytelling, not
  disaster tourism. Focus on the fascinating chain of causes, not the suffering itself.
- No graphic descriptions of injuries, deaths, or suffering. Mention that people were hurt
  or killed factually and briefly; don't dwell on it.
- Original wording only — never copy phrasing from a specific Wikipedia article, documentary,
  or news report. The facts are public record; the words are always yours.
- Structure: hook → brief setup (what, where, when) → the chain of causes (the fascinating
  part) → what changed because of it → brief close.
- 5-7 beats, each 1-2 sentences.
- Open with a hook line naturally adapting the style fragment you're given.
- Close with a one-line "follow for more" nudge.
- Short sentences, no headers, no bullet points. Engaging and clear.
- For the hook AND each beat, pick a short visually-literal stock-footage phrase
  (e.g. "industrial factory interior", "airport runway aerial view", "structural steel beams",
  "control room warning lights", "engineering blueprints close up") — atmospheric and relevant,
  never graphic or depicting the actual accident victims.
- Call the submit_accident_video tool exactly once."""

ACCIDENT_TOOL = {
    "name": "submit_accident_video",
    "description": "Submit the finished accident/disaster video: hook, story beats with visual cues, and upload metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "premise": {"type": "string", "description": "One-sentence summary of which event this covers, used only to avoid repeating the same event too often"},
            "title": {"type": "string", "description": "<=95 characters, specific and dramatic, leads with the event name or most striking detail"},
            "description": {"type": "string", "description": "2-3 sentences plus a follow nudge"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "8-12 lowercase tags relevant to this event"},
            "hashtags": {"type": "array", "items": {"type": "string"}, "description": "5-8 hashtags starting with #, always include #shorts"},
            "hook": {"type": "string", "description": "The opening hook line, 1 short sentence"},
            "hook_visual_query": {"type": "string", "description": "Concrete, atmospheric, non-graphic stock-footage search phrase for the hook"},
            "beats": {
                "type": "array",
                "minItems": 5,
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "properties": {
                        "narration": {"type": "string", "description": "1-2 sentences for this story beat"},
                        "visual_query": {"type": "string", "description": "Concrete, atmospheric, non-graphic stock-footage search phrase for this beat"},
                    },
                    "required": ["narration", "visual_query"],
                },
            },
        },
        "required": ["premise", "title", "description", "tags", "hashtags", "hook", "hook_visual_query", "beats"],
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


def generate_accident_video() -> dict:
    used_premises = _load_used_premises()
    avoid_text = (
        "Avoid these recently-covered events — pick a different one:\n" + "\n".join(f"- {p}" for p in used_premises[-20:])
        if used_premises else "No prior events to avoid yet."
    )
    hook_sample = random.choice(HOOK_STYLES)
    topic_suggestion = random.choice(HIGH_INTEREST_TOPICS)

    user_prompt = f"""Write today's accident/disaster video.

{avoid_text}

Suggested topic or category (use this or pick a different well-known shocking accident if it was covered recently): {topic_suggestion}

Hook style to adapt for the opening line (sentence fragment — work it into a natural full sentence matching the event):
"{hook_sample}"

Example: if the event is the Gimli Glider and the hook fragment is "happened because of one decision nobody expected to matter", a good opener might be: "A simple unit conversion error almost brought down a fully loaded passenger jet." Adapt naturally — don't recite it verbatim."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[ACCIDENT_TOOL],
        tool_choice={"type": "tool", "name": "submit_accident_video"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    video = dict(tool_use_block.input)

    if not any(h.lower() == "#shorts" for h in video.get("hashtags", [])):
        video.setdefault("hashtags", []).append("#shorts")

    _save_used_premise(video["premise"])
    return video


if __name__ == "__main__":
    print(json.dumps(generate_accident_video(), indent=2))
