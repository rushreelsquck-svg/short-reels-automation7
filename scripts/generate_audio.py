"""
generate_audio.py
Free TTS per scene (gTTS) — generating one clip per scene rather than one
long clip for the whole story means each scene's image gets to stay on
screen for exactly as long as its own narration takes, no guessing at split
points in a single audio file.
"""
from pathlib import Path

from gtts import gTTS


def generate_voiceover(text: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    gTTS(text=text, lang="en", slow=False).save(output_path)
    return output_path


if __name__ == "__main__":
    generate_voiceover("Once, behind a quiet village, a small cat found something unexpected.", "/tmp/test_scene_audio.mp3")
    print("Saved /tmp/test_scene_audio.mp3")
