# The Case File — Daily True Crime Bot

Automatically writes a respectful, factual retelling of a closed,
well-documented true crime case each day — a measured hook, 5-7 chronological
story beats (setup, the crime, the investigation, the resolution, a brief
reflection), real non-graphic stock footage per beat — and uploads it to
YouTube. Fully generative, like the facts/history channels, not a news feed.

---

## Read this before turning the schedule on

True crime is a genre where getting it wrong has real consequences — for
real people, not just for the channel. This is the most restrictive system
prompt of any channel in this family, on purpose. Before loosening any of
these rules, think it through, don't just tweak it:

- **Only closed cases.** The prompt explicitly requires a confirmed legal
  outcome (conviction, plea, etc.) and well-established public documentation.
  It's told to never touch an active or unsolved case.
- **Never states guilt without a conviction.** Anyone not actually convicted
  doesn't get described as guilty, full stop.
- **No child victims, no graphic sexual violence.** The prompt is told to
  skip these cases entirely and pick a different one.
- **No gore, no gratuitous violence detail, no crime "how-to" detail.** The
  focus is the investigation and resolution, not the violence itself.
- **Respectful, measured tone.** Not breathless, not "true crime but make it
  fun" — victims are people, not entertainment.

Spot-check outputs more carefully here than you would for the other
channels. This system prompt reduces risk significantly, but it's still an
LLM writing about real tragedies with no human review before publishing —
that calls for real ongoing attention, not "set and forget."

---

## What this actually does (and doesn't do)

- ✅ Retells a different closed case each day, original wording, drawn from
  well-established public record (the facts aren't copyrightable, but the
  writing is always original — never reskins a specific article/book/doc).
- ✅ Real, deliberately non-graphic stock footage per beat (police lights,
  courthouse exteriors, archive-style newspaper shots) — no violence, no
  weapons, nothing graphic, by design.
- ❌ Does **not** cover ongoing/unsolved cases, ever.
- ❌ Does **not** guarantee any subscriber count — same honest caveat as
  every channel in this family, but worth repeating: virality isn't a true
  crime channel's actual goal anyway. Trust and credibility are, and those
  take longer to build and are much easier to destroy with one bad video.

---

## Setup

Same pattern as Billion Meaning / Vaults of History — reuse
`ANTHROPIC_API_KEY` and `YT_API_KEY` as-is, new `YT_REFRESH_TOKEN` for this
channel's account, `PEXELS_API_KEY` strongly recommended (this format leans
on real footage, same reasoning as the other generative channels).

### Step 1: Pexels API key

Sign up free at [pexels.com/api](https://www.pexels.com/api/), grab the key.

### Step 2: YouTube OAuth

```powershell
$env:YT_CLIENT_ID = "your-client-id"
$env:YT_CLIENT_SECRET = "your-client-secret"
venv\Scripts\python.exe scripts\get_oauth_token.py
```

Log into *this* channel's Google account when the browser opens.

### Step 3: Push to GitHub and add secrets

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | reuse existing |
| `YT_CLIENT_ID` / `YT_CLIENT_SECRET` | reuse existing |
| `YT_REFRESH_TOKEN` | new, from Step 2 |
| `PEXELS_API_KEY` | from Step 1 |
| `YT_API_KEY` | optional |

### Step 4: Test it, and actually read the output

Actions tab → "The Case File - Daily True Crime" → **Run workflow**. For
this channel specifically, don't just check that it ran — read the actual
script in the video before trusting the schedule. Confirm it picked a real,
closed case and didn't drift into speculation.

---

## Customizing

- **Case selection & tone**: all guardrails live in `scripts/generate_case.py`'s
  system prompt. If you tighten or loosen anything here, re-read the whole
  rule list — these rules interact with each other.
- **How videos go public**: `YT_PRIVACY_STATUS` works like the other
  channels — `scheduled` (default), `unlisted`, or `public`. Given the
  subject matter, you may want a longer review window than the default
  3 hours; `YT_PUBLISH_DELAY_HOURS` controls that.
