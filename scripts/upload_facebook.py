"""
upload_facebook.py
Cross-posts the finished video to a Facebook Page as a Reel, via Meta's
official Resumable Upload + Reels Publishing API (3 steps: start session,
upload bytes, publish).

This runs AFTER the YouTube upload, and is deliberately non-fatal: if
anything here fails, it's logged and the pipeline still finishes
successfully (the YouTube upload already happened by this point).

Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN in the repo secrets.
If neither is set, this step is silently skipped.
"""
import os

import requests

FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
GRAPH_API_VERSION = "v21.0"
MAX_DESCRIPTION_CHARS = 2200


def upload_reel(video_path: str, description: str) -> str | None:
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Facebook cross-post skipped — FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN not set.")
        return None

    try:
        # Step 1: start the upload session
        start_resp = requests.post(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/video_reels",
            json={"upload_phase": "start", "access_token": FB_PAGE_ACCESS_TOKEN},
            timeout=30,
        )
        start_resp.raise_for_status()
        video_id = start_resp.json()["video_id"]

        # Step 2: upload the file bytes
        file_size = os.path.getsize(video_path)
        with open(video_path, "rb") as f:
            file_bytes = f.read()

        upload_resp = requests.post(
            f"https://rupload.facebook.com/video-upload/{GRAPH_API_VERSION}/{video_id}",
            headers={
                "Authorization": f"OAuth {FB_PAGE_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream",
            },
            data=file_bytes,
            timeout=300,
        )
        upload_resp.raise_for_status()
        if not upload_resp.json().get("success"):
            raise RuntimeError(f"upload step did not return success: {upload_resp.text}")

        # Step 3: publish
        publish_resp = requests.post(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/video_reels",
            params={
                "access_token": FB_PAGE_ACCESS_TOKEN,
                "video_id": video_id,
                "upload_phase": "finish",
                "video_state": "PUBLISHED",
                "description": (description or "")[:MAX_DESCRIPTION_CHARS],
            },
            timeout=30,
        )
        publish_resp.raise_for_status()
        if not publish_resp.json().get("success"):
            raise RuntimeError(f"publish step did not return success: {publish_resp.text}")

        print(f"Cross-posted to Facebook as a Reel: video_id={video_id}")
        return video_id

    except Exception as e:
        print(f"Facebook cross-post failed (non-fatal — YouTube upload already succeeded): {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python upload_facebook.py /path/to/video.mp4")
        sys.exit(1)
    upload_reel(sys.argv[1], "Test cross-post. Safe to delete.")
