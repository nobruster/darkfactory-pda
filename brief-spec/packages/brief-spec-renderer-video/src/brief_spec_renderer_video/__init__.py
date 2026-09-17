from __future__ import annotations

import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from briefspec.artifacts import canonical_json_bytes, sha256_bytes
from briefspec.state import atomic_write_many

__version__ = "0.1.0"


def capabilities() -> dict[str, Any]:
    try:
        import playwright  # noqa: F401
    except ImportError:
        playwright_ready = False
    else:
        playwright_ready = True
    tools = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe")}
    return {
        "renderer": "video",
        "renderer_version": __version__,
        "media_type": "video/mp4",
        "playwright": playwright_ready,
        "tools": tools,
        "ready": playwright_ready and all(tools.values()),
        "network_default": False,
    }


def _probe(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required for Chronicle video verification")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def _scenes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    requested = [item for item in snapshot["decisions"] if item["state"] == "requested"]
    open_drift = [item for item in snapshot["drift"] if item["disposition"] == "open"]
    intent = [item["headline"] for item in snapshot["intent_anchors"]]
    values = [
        {
            "id": "intent",
            "title": "Intent",
            "items": intent or ["No explicit intent anchor was observed."],
        },
        {
            "id": "state",
            "title": "Where the project is now",
            "items": [
                f"Method: {snapshot['current_state']['method']}",
                f"Phase: {snapshot['current_state']['phase'] or 'unavailable'}",
                snapshot["current_state"]["headline"],
            ],
        },
        {
            "id": "milestones",
            "title": "Completed with proof",
            "items": [item["headline"] for item in snapshot["milestones"]]
            or ["No completed milestone was observed."],
        },
        {
            "id": "drift",
            "title": "Detours and drift",
            "items": [item["observed"] for item in open_drift] or ["No open drift was observed."],
        },
        {
            "id": "decisions",
            "title": "Human decisions",
            "items": [str(item.get("question") or item["decision_id"]) for item in requested]
            or ["No human decision is currently requested."],
        },
        {
            "id": "next",
            "title": "What happens next",
            "items": snapshot["next_actions"] or ["No explicit next action was observed."],
        },
    ]
    for scene in values:
        scene["narration"] = f"{scene['title']}. " + ". ".join(scene["items"])
    return values


def _scene_html(scene: dict[str, Any], project: str, index: int, total: int) -> str:
    items = "".join(f"<li>{html.escape(str(item))}</li>" for item in scene["items"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; }} body {{ margin: 0; width: 1600px; height: 900px;
 background: #f2eee5; color: #17201d; font-family: Arial, sans-serif; }}
main {{ height: 100%; padding: 72px 88px; display: grid; grid-template-rows: auto 1fr auto; }}
.eyebrow {{ color: #1b5948; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
h1 {{ font-size: 76px; line-height: 1; max-width: 1200px; margin: 40px 0 54px; }}
ul {{ font-size: 34px; line-height: 1.35; max-width: 1250px; margin: 0; padding-left: 44px; }}
li {{ margin: 18px 0; }} footer {{ display: flex; justify-content: space-between;
 font-size: 22px; color: #5a625e; }}
</style></head><body><main><div><p class="eyebrow">{html.escape(project)} · Project Chronicle</p>
<h1>{html.escape(str(scene["title"]))}</h1><ul>{items}</ul></div><div></div>
<footer><span>Brief-Spec Human Review Pack</span><span>{index + 1} / {total}</span></footer>
</main></body></html>"""


def _vtt(scenes: list[dict[str, Any]], seconds: float) -> str:
    def stamp(value: float) -> str:
        milliseconds = round(value * 1000)
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, millis = divmod(remainder, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"

    duration = seconds / len(scenes)
    values = ["WEBVTT", ""]
    for index, scene in enumerate(scenes):
        values.extend(
            [
                f"{stamp(index * duration)} --> {stamp((index + 1) * duration)}",
                str(scene["narration"]),
                "",
            ]
        )
    return "\n".join(values)


def render_chronicle_video(
    snapshot: dict[str, Any],
    output: Path,
    *,
    provider: str = "macos",
    voice: str | None = None,
    rate: int = 190,
    consent_network: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    sidecar_paths = [
        output.with_suffix(".storyboard.json"),
        output.with_suffix(".vtt"),
        output.with_suffix(".txt"),
    ]
    conflicts = [path for path in [output, *sidecar_paths] if path.exists() and not force]
    if conflicts:
        raise FileExistsError(f"Refusing to overwrite existing output: {conflicts[0]}")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required for Chronicle video output")
    from briefspec_renderer_audio import render_script_document
    from playwright.sync_api import sync_playwright

    scenes = _scenes(snapshot)
    transcript = "\n\n".join(scene["narration"] for scene in scenes) + "\n"
    created_at = str(snapshot["window"]["created_at"])
    with tempfile.TemporaryDirectory(prefix="brief-spec-video-") as temporary:
        root = Path(temporary)
        audio = root / "narration.mp3"
        audio_record = render_script_document(
            transcript,
            audio,
            created_at=created_at,
            provider=provider,
            voice=voice,
            rate=rate,
            consent_network=consent_network,
        )
        duration = float(audio_record["metadata"]["duration_seconds"])
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            chromium_version = browser.version
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            for index, scene in enumerate(scenes):
                source = root / f"scene-{index:02}.html"
                source.write_text(
                    _scene_html(scene, str(snapshot["project"]["name"]), index, len(scenes)),
                    encoding="utf-8",
                )
                page.goto(source.as_uri(), wait_until="load")
                page.screenshot(path=str(root / f"scene-{index:02}.png"))
            browser.close()
        scene_duration = duration / len(scenes)
        concat = []
        for index in range(len(scenes)):
            concat.append(f"file '{root / f'scene-{index:02}.png'}'")
            concat.append(f"duration {scene_duration:.6f}")
        concat.append(f"file '{root / f'scene-{len(scenes) - 1:02}.png'}'")
        (root / "scenes.txt").write_text("\n".join(concat) + "\n", encoding="utf-8")
        ffmeta = [";FFMETADATA1"]
        for index, scene in enumerate(scenes):
            ffmeta.extend(
                [
                    "[CHAPTER]",
                    "TIMEBASE=1/1000",
                    f"START={round(index * scene_duration * 1000)}",
                    f"END={round((index + 1) * scene_duration * 1000)}",
                    f"title={scene['title']}",
                ]
            )
        (root / "chapters.ffmeta").write_text("\n".join(ffmeta) + "\n", encoding="utf-8")
        rendered = root / "chronicle.mp4"
        command = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(root / "scenes.txt"),
            "-i",
            str(audio),
            "-i",
            str(root / "chapters.ffmeta"),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map_metadata",
            "2",
            "-vf",
            "fps=30,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-threads",
            "1",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            "-metadata",
            f"creation_time={created_at}",
            str(rendered),
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=900, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffmpeg video rendering failed")
        content = rendered.read_bytes()
    storyboard, captions, transcript_path = sidecar_paths
    storyboard_value = {
        "schema_version": "brief-spec-video-storyboard/1.0",
        "canonical_sha256": snapshot["canonical_sha256"],
        "created_at": created_at,
        "scenes": scenes,
    }
    sidecars = {
        storyboard: json.dumps(storyboard_value, indent=2, sort_keys=True).encode() + b"\n",
        captions: _vtt(scenes, duration).encode(),
        transcript_path: transcript.encode(),
    }
    atomic_write_many(
        [(output, content, 0o644), *[(path, value, 0o644) for path, value in sidecars.items()]]
    )
    probe = _probe(output)
    metadata = {
        "renderer": "video",
        "renderer_version": __version__,
        "source_snapshot_sha256": snapshot["canonical_sha256"],
        "source_storyboard_sha256": sha256_bytes(canonical_json_bytes(storyboard_value)),
        "source_script_sha256": sha256_bytes(transcript.encode()),
        "canonical_created_at": created_at,
        "chromium_version": chromium_version,
        "ffmpeg_version": subprocess.run(
            [ffmpeg, "-version"], text=True, capture_output=True, timeout=30, check=False
        ).stdout.splitlines()[0],
        "duration_seconds": duration,
        "frame_size": "1600x900",
        "frame_rate": 30,
        "ai_generated_speech": True,
        "renderer_fingerprint_required_for_byte_determinism": True,
        "sidecars": [
            {"path": path.name, "sha256": sha256_bytes(content)}
            for path, content in sidecars.items()
        ],
        "probe": probe,
    }
    return {
        "format": "video",
        "path": output.name,
        "media_type": "video/mp4",
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
        "renderer_version": __version__,
        "metadata": metadata,
    }


def verify_video(path: Path) -> dict[str, Any]:
    try:
        value = _probe(path)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "detail": str(exc)}
    streams = value.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    duration = float(value.get("format", {}).get("duration", 0))
    sidecars = [
        path.with_suffix(".storyboard.json"),
        path.with_suffix(".vtt"),
        path.with_suffix(".txt"),
    ]
    errors = []
    if not video or video.get("codec_name") != "h264":
        errors.append("H.264 video stream is missing")
    if not audio or audio.get("codec_name") != "aac":
        errors.append("AAC audio stream is missing")
    if not video or (video.get("width"), video.get("height")) != (1600, 900):
        errors.append("Video resolution must be 1600x900")
    if duration <= 0:
        errors.append("Video duration is invalid")
    for sidecar in sidecars:
        if not sidecar.is_file() or not sidecar.read_bytes():
            errors.append(f"Video sidecar is missing or empty: {sidecar.name}")
    return {
        "status": "FAIL" if errors else "PASS",
        "detail": "; ".join(errors) if errors else f"H.264/AAC video verified; {duration:.2f}s",
        "errors": errors,
        "duration_seconds": duration,
    }
