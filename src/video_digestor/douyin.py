import json
import re
import logging
from pathlib import Path
from urllib.parse import quote, urlencode

from video_digestor.abogus import ABogus
from video_digestor.utils import run_cmd

log = logging.getLogger(__name__)

_DOUYIN_AWEME_API = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
_DOUYIN_VIDEO_RE = re.compile(r"douyin\.com/(?:video/(\d+)|discover\?.*?modal_id=(\d+)|jingxuan\?.*?modal_id=(\d+))")


def _extract_aweme_id(url: str) -> str | None:
    m = _DOUYIN_VIDEO_RE.search(url)
    if not m:
        return None
    return m.group(1) or m.group(2) or m.group(3)


def _get_browser_cookies(browser: str) -> dict[str, str]:
    from yt_dlp.cookies import extract_cookies_from_browser
    jar = extract_cookies_from_browser(browser)
    cookies: dict[str, str] = {}
    for c in jar:
        if "douyin" in c.domain:
            cookies[c.name] = c.value
    return cookies


def _cookies_to_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def _build_aweme_params(aweme_id: str) -> dict:
    return {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "aweme_id": aweme_id,
        "pc_client_type": "1",
        "version_code": "170400",
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "screen_width": "1920",
        "screen_height": "1080",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_version": "124.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "124.0.0.0",
        "os_name": "Windows",
        "os_version": "10",
        "cpu_core_num": "8",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "10",
        "effective_type": "4g",
        "round_trip_time": "100",
    }


def get_douyin_info(
    url: str,
    cookies_from_browser: str = "chrome",
) -> dict:
    aweme_id = _extract_aweme_id(url)
    if not aweme_id:
        raise ValueError(f"Cannot extract aweme_id from URL: {url}")

    cookies = _get_browser_cookies(cookies_from_browser)
    log.debug("Loaded %d Douyin cookies from %s", len(cookies), cookies_from_browser)

    params = _build_aweme_params(aweme_id)
    abogus = ABogus()
    a_bogus = abogus.get_value(params)
    a_bogus_encoded = quote(a_bogus, safe='')
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    url = f"{_DOUYIN_AWEME_API}?{urlencode(params)}&a_bogus={a_bogus_encoded}"

    result = run_cmd([
        "curl", "-s",
        "-H", f"User-Agent: {ua}",
        "-H", f"Cookie: {_cookies_to_header(cookies)}",
        "-H", "Referer: https://www.douyin.com/",
        url,
    ])

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Douyin API returned invalid JSON. Response: {result.stdout[:200]}"
        )

    detail = data.get("aweme_detail")
    if not detail:
        raise RuntimeError(
            "Douyin API did not return aweme_detail. "
            "Cookies may be expired -- try logging into douyin.com in your browser first."
        )

    info = {
        "id": str(detail.get("aweme_id", aweme_id)),
        "title": detail.get("desc", detail.get("preview_title", "")),
        "duration": detail.get("duration", 0) / 1000.0,
        "uploader": (
            detail.get("author", {}).get("nickname", "")
            if isinstance(detail.get("author"), dict)
            else ""
        ),
        "subtitles": [],
        "automatic_captions": [],
        "formats": [
            {
                "format_id": "douyin_web",
                "ext": "mp4",
                "resolution": "",
                "filesize": None,
                "audio_ext": "mp4a",
            }
        ],
        "url": url,
        "_raw": detail,
    }

    if detail.get("desc"):
        log.info("Video description (caption) available: %s chars", len(detail["desc"]))

    return info


def get_douyin_description(
    url: str,
    cookies_from_browser: str = "chrome",
) -> str | None:
    info = get_douyin_info(url, cookies_from_browser=cookies_from_browser)
    raw = info.get("_raw", {})
    desc = raw.get("desc", "")
    return desc if desc else None


def download_douyin_audio(
    url: str,
    out_dir: Path,
    cookies_from_browser: str = "chrome",
) -> Path | None:
    info = get_douyin_info(url, cookies_from_browser=cookies_from_browser)
    raw = info.get("_raw", {})
    title = info["title"] or raw.get("aweme_id", "douyin_video")

    video = raw.get("video", {})
    play_addr = video.get("play_addr", {}) or video.get("play_addr_h264", {})
    url_list = play_addr.get("url_list", [])

    if not url_list:
        bit_rates = video.get("bit_rate", [])
        if bit_rates:
            url_list = bit_rates[0].get("play_addr", {}).get("url_list", [])

    if not url_list:
        log.warning("No video URL found in Douyin API response")
        return None

    video_url = url_list[0]
    log.info("Downloading video from: %s ...", video_url[:80])

    safe_title = re.sub(r'[\\/:*?"<>|\s]+', '_', title)[:80]
    mp3_path = out_dir / f"{safe_title}.mp3"

    run_cmd([
        "ffmpeg", "-y",
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-i", video_url,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        str(mp3_path),
    ], timeout=300)

    log.info("Audio downloaded: %s", mp3_path)
    return mp3_path
