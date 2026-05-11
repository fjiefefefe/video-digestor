import json
import logging
from pathlib import Path

from video_digestor.utils import run_cmd, ensure_ytdlp, ensure_ffmpeg, sanitize_dirname

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_base_cmd(
    url: str,
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
        if "youtube.com" in url or "youtu.be" in url:
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
    """Fetch video metadata using yt-dlp (no download). Uses Douyin API for douyin.com URLs."""
    if "douyin.com" in url:
        from video_digestor.douyin import get_douyin_info
        browser = cookies_from_browser or "chrome"
        return get_douyin_info(url, cookies_from_browser=browser)

    ensure_ytdlp()
    cmd = _build_base_cmd(url, cookies_from_browser, cookies_file, js_runtimes)
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

    策略：
    1. 先按用户指定的语言下载
    2. 若无匹配，尝试补全语言变体（zh → zh-Hans, zh-CN 等）
    3. 仍无则不加语言限制，全部下载
    按 人工字幕 → 自动字幕 顺序尝试。
    """
    if "douyin.com" in url:
        return None

    ensure_ytdlp()
    expanded_langs = _expand_langs(langs)

    lang_attempts: list[tuple[str, str | None]] = [
        ("指定语言", ",".join(langs)),
    ]
    if expanded_langs != langs:
        lang_attempts.append(("扩展语言", ",".join(expanded_langs)))
    lang_attempts.append(("全部语言", None))

    for sub_type, flag in [
        ("manual", "--write-subs"),
        ("auto", "--write-auto-subs"),
    ]:
        for attempt_label, lang_str in lang_attempts:
            if not lang_str:
                continue

            log.info("尝试 %s 字幕（%s: %s）...", sub_type, attempt_label, lang_str)
            try:
                cmd = _build_base_cmd(url, cookies_from_browser, cookies_file, js_runtimes)
                cmd += [
                    "--skip-download",
                    flag,
                ]
                if lang_str is not None:
                    cmd += ["--sub-lang", lang_str]
                cmd += [
                    "--no-playlist",
                    "--output", f"{out_dir}/%(title)s.%(ext)s",
                    url,
                ]
                run_cmd(cmd)
            except RuntimeError as e:
                log.warning("  失败: %s", str(e).split("\n")[0])
                continue

            sub_files = _find_subtitle_files(out_dir)
            if sub_files:
                sub_file = sub_files[0]
                log.info("  获取到: %s", sub_file.name)
                target = out_dir / "raw_subtitle.srt"
                _convert_to_srt(sub_file, target)
                log.info("  保存为: %s", target.name)
                return target

    log.info("未找到任何字幕")
    if "bilibili.com" in url and not cookies_from_browser and not cookies_file:
        log.info("💡 B站视频可能需要登录才能拿到AI字幕，试试:")
        log.info("   video-digestor run URL --cookies-from-browser chrome")
    return None


def _expand_langs(langs: list[str]) -> list[str]:
    """将短语言代码展开为常见变体，提高匹配概率。

    包含 B 站专用 AI 字幕代码 (ai-zh, ai-en) 和弹幕。
    """
    variants = {
        "zh": ["zh", "zh-Hans", "zh-CN", "zh-Hant", "zh-TW", "zh-HK", "ai-zh"],
        "en": ["en", "en-US", "en-GB", "en-orig", "ai-en"],
        "ja": ["ja", "ja-JP"],
        "ko": ["ko", "ko-KR"],
    }
    result = []
    seen = set()
    for lang in langs:
        for v in variants.get(lang, [lang]):
            if v not in seen:
                result.append(v)
                seen.add(v)
    return result


def _find_subtitle_files(out_dir: Path) -> list[Path]:
    """Return sorted list of downloaded subtitle files (any format)."""
    return sorted(
        f for f in out_dir.glob("*")
        if f.suffix.lower() in (".srt", ".vtt", ".ass", ".ssa")
    )


def _convert_to_srt(src: Path, target: Path) -> None:
    """Convert any subtitle format to .srt, or just rename if already .srt."""
    if src.suffix.lower() == ".srt":
        if src != target:
            src.rename(target)
    elif src.suffix.lower() == ".vtt":
        _vtt_to_srt(src, target)
        src.unlink()
    else:
        src.rename(target)


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
    if "douyin.com" in url:
        from video_digestor.douyin import download_douyin_audio
        browser = cookies_from_browser or "chrome"
        return download_douyin_audio(url, out_dir, cookies_from_browser=browser)

    ensure_ytdlp()
    ensure_ffmpeg()

    log.info("Downloading audio from %s ...", url)
    cmd = _build_base_cmd(url, cookies_from_browser, cookies_file, js_runtimes)
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
