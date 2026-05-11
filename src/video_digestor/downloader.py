import json
import logging
from pathlib import Path

from video_digestor.utils import run_cmd, ensure_ytdlp, ensure_ffmpeg, sanitize_dirname

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_base_cmd(
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
    js_runtimes: str | None = None,
) -> list[str]:
    """Build base yt-dlp command with optional cookie and JS flags."""
    cmd = ["yt-dlp"]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    elif cookies_file:
        cmd += ["--cookies", str(cookies_file)]
    if js_runtimes:
        cmd += ["--js-runtimes", js_runtimes]
        cmd += ["--remote-components", "ejs:github"]
    return cmd


# ---------------------------------------------------------------------------
# Video info
# ---------------------------------------------------------------------------

def get_video_info(
    url: str,
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
    js_runtimes: str | None = None,
) -> dict:
    """Fetch video metadata using yt-dlp (no download)."""
    ensure_ytdlp()
    cmd = _build_base_cmd(cookies_from_browser, cookies_file, js_runtimes)
    cmd += [
        "--dump-json",
        "--no-download",
        "--no-playlist",
        url,
    ]
    result = run_cmd(cmd)
    info = json.loads(result.stdout)
    return {
        "id": info.get("id", ""),
        "title": info.get("title", ""),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", ""),
        "subtitles": list(info.get("subtitles", {}).keys()),
        "automatic_captions": list(info.get("automatic_captions", {}).keys()),
        "formats": [
            {
                "format_id": f.get("format_id", ""),
                "ext": f.get("ext", ""),
                "resolution": f.get("resolution", ""),
                "filesize": f.get("filesize"),
                "audio_ext": f.get("audio_ext", ""),
            }
            for f in info.get("formats", [])
        ],
        "url": info.get("webpage_url", url),
    }


def has_audio_formats(info: dict) -> bool:
    """Check if any format has an audio codec."""
    return any(f.get("audio_ext") != "none" for f in info.get("formats", []))


# ---------------------------------------------------------------------------
# Subtitle download
# ---------------------------------------------------------------------------

def download_subtitles(
    url: str,
    out_dir: Path,
    langs: list[str],
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
    js_runtimes: str | None = None,
) -> Path | None:
    """Download subtitles using yt-dlp. Returns path to .srt file or None.

    Tries manual subtitles first, falls back to automatic captions.
    """
    ensure_ytdlp()
    lang_str = ",".join(langs)

    for sub_type, flag in [
        ("manual", "--write-subs"),
        ("auto", "--write-auto-subs"),
    ]:
        log.info("Trying %s subtitles (langs: %s)...", sub_type, lang_str)
        try:
            cmd = _build_base_cmd(cookies_from_browser, cookies_file, js_runtimes)
            cmd += [
                "--skip-download",
                flag,
                "--sub-lang", lang_str,
                "--no-playlist",
                "--output", f"{out_dir}/%(title)s.%(ext)s",
                url,
            ]
            run_cmd(cmd)
        except RuntimeError as e:
            log.warning("%s subtitles failed: %s", sub_type, e)
            continue

        sub_files = sorted(out_dir.glob("*.vtt")) + sorted(out_dir.glob("*.srt"))
        if sub_files:
            sub_file = sub_files[0]
            log.info("Downloaded subtitle: %s", sub_file)

            target = out_dir / "raw_subtitle.srt"
            if sub_file.suffix == ".vtt":
                _vtt_to_srt(sub_file, target)
                sub_file.unlink()
            elif sub_file != target:
                sub_file.rename(target)
            log.info("Saved as: %s", target)
            return target

    return None


def _vtt_to_srt(vtt_path: Path, srt_path: Path) -> None:
    """Convert a WebVTT subtitle file to SRT format."""
    lines = vtt_path.read_text(encoding="utf-8").splitlines()
    srt_lines = []
    idx = 1

    for line in lines:
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            ts = line.replace(".", ",")
            srt_lines.append(str(idx))
            srt_lines.append(ts)
            idx += 1
        else:
            srt_lines.append(line)

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Audio download
# ---------------------------------------------------------------------------

def download_audio(
    url: str,
    out_dir: Path,
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
    js_runtimes: str | None = None,
) -> Path | None:
    """Download audio-only from a video URL. Returns path to audio file."""
    ensure_ytdlp()
    ensure_ffmpeg()

    log.info("Downloading audio from %s ...", url)
    cmd = _build_base_cmd(cookies_from_browser, cookies_file, js_runtimes)
    cmd += [
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--no-playlist",
        "--output", f"{out_dir}/%(title)s.%(ext)s",
        url,
    ]
    run_cmd(cmd)

    audio_files = sorted(out_dir.glob("*.mp3"))
    if not audio_files:
        log.warning("No audio file found after download.")
        return None

    log.info("Audio downloaded: %s", audio_files[0])
    return audio_files[0]
