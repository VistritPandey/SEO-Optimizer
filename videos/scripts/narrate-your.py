"""Generate optional system-voice narration; committed audio makes rendering portable."""

import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT.parent / ".data/customer-narration"
TEMP.mkdir(parents=True, exist_ok=True)
STORIES = [
    (
        "ONGOING SEO CARE",
        "Your website changes. Your SEO needs to keep up.",
        "Your website changes all the time. Your SEO needs to keep up.",
    ),
    (
        "01 · THE WEBSITE UPDATE",
        "A new homepage. A broken next step.",
        "Your team merges a homepage update. It looks good, but the main shopping "
        "button now leads to a missing page.",
    ),
    (
        "02 · CHECK WHAT CHANGED",
        "The agent confirms what needs attention.",
        "Your Optimiser checks the changed page and follows its links. It confirms the "
        "broken link and a missing page description.",
    ),
    (
        "03 · PREPARE A FOCUSED FIX",
        "Keep the design. Repair the problem.",
        "The agent reads the existing website, restores the working link, and writes a "
        "description using the page's own content. It tests the proposed changes.",
    ),
    (
        "04 · YOUR TEAM REVIEWS",
        "A clear fix. Your decision.",
        "Your team reviews a focused fix, with a clear explanation of what changed and "
        "why. You choose when it goes live.",
    ),
    (
        "05 · VERIFY AFTER DEPLOYMENT",
        "The fix is live. Does it actually work?",
        "After deployment, the agent checks the website again. The collection opens, "
        "and the page description is restored. That closes this issue.",
    ),
    (
        "06 · THE NEXT UPDATE",
        "Nothing broken? Nothing to rewrite.",
        "The next update only changes the spacing. Your Optimiser checks it and leaves "
        "it alone. No unnecessary fix or review.",
    ),
    (
        "THE WORK KEEPS GOING",
        "You keep building. We keep watching.",
        "Checks continue between updates, too. Your team keeps building. Your Optimiser "
        "keeps watching.",
    ),
]
result = []
for i, (chapter, title, narration) in enumerate(STORIES):
    script = TEMP / f"{i}.txt"
    raw = TEMP / f"{i}.aiff"
    script.write_text(narration)
    dest = ROOT / "public/customer" / f"voice-{i}.mp3"
    subprocess.run(
        ["say", "-v", "Daniel", "-r", "172", "-f", str(script), "-o", str(raw)], check=True
    )
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(raw),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-b:a",
            "128k",
            str(dest),
        ],
        check=True,
    )
    seconds = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(dest),
            ],
            text=True,
        )
    )
    result.append(
        {
            "chapter": chapter,
            "title": title,
            "narration": narration,
            "audio": f"customer/voice-{i}.mp3",
            "frames": math.ceil((seconds + 1.5) * 30),
            "audio_seconds": seconds,
        }
    )
(ROOT / "public/customer/story.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    "Generated",
    len(result),
    "narrated scenes;",
    sum(item["frames"] for item in result) / 30,
    "seconds",
)
