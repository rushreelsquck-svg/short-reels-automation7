"""
main.py
Runs the whole daily case pipeline end to end. Each stage prints progress
so failures are easy to spot in the Actions log.
"""
import json
import os
import sys
import traceback
from pathlib import Path

from generate_case import generate_case_video
from generate_audio import generate_voiceover
from build_video import build_video
from fetch_youtube_trending_tags import get_trending_keywords
from youtube_metadata import build_final_metadata
from upload_video import upload_short

WORKDIR = Path("/tmp/case_run")


def run():
    print("[1/5] Writing today's case video (Claude)...")
    video = generate_case_video()
    print(f"      -> {video['title']}  ({len(video['beats'])} beats)")

    WORKDIR.mkdir(parents=True, exist_ok=True)
    scenes = []

    print("[2/5] Generating voiceover for the hook and each beat...")
    hook_audio = str(WORKDIR / "scene_hook.mp3")
    generate_voiceover(video["hook"], hook_audio)
    scenes.append({"audio_path": hook_audio, "visual_query": None, "caption_text": video["hook"], "number": None})

    for i, beat in enumerate(video["beats"]):
        audio_path = str(WORKDIR / f"scene_{i}.mp3")
        generate_voiceover(beat["narration"], audio_path)
        scenes.append({
            "audio_path": audio_path,
            "visual_query": beat["visual_query"],
            "caption_text": beat["narration"],
            "number": i + 1,
        })
    print(f"      -> {len(scenes)} scenes ready (hook + {len(video['beats'])} beats)")

    print("[3/5] Building the video...")
    video_path = str(WORKDIR / "output.mp4")
    build_video(scenes, video_path)

    print("[4/5] Fetching trending keywords for tag enrichment...")
    trending_keywords = get_trending_keywords(region=os.environ.get("NEWS_REGION", "US"))
    print(f"      -> {len(trending_keywords)} keywords found")

    print("[5/5] Uploading to YouTube...")
    final_meta = build_final_metadata(video, trending_keywords)
    video_id = upload_short(
        video_path=video_path,
        title=final_meta["title"],
        description=final_meta["description"],
        tags=final_meta["tags"],
    )

    print(json.dumps({"video_id": video_id, "title": final_meta["title"]}, indent=2))
    return video_id


if __name__ == "__main__":
    try:
        run()
    except Exception:
        print("PIPELINE FAILED:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
