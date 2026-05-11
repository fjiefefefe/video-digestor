import subprocess
import shutil
import re
import json
import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
log = logging.getLogger("video-digestor")


# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run a shell command with error handling. Returns CompletedProcess on success.

    Raises RuntimeError if the command fails.
    """
    log.debug("Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"Command not found: {cmd[0]}. Please install it first."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(cmd)}\n{stderr}"
        )
    return result


def cmd_exists(name: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(name) is not None


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------

def ensure_ytdlp():
    if not cmd_exists("yt-dlp"):
        raise RuntimeError(
            "yt-dlp is not installed.\n"
            "  Install: pip install yt-dlp\n"
            "  Or visit: https://github.com/yt-dlp/yt-dlp"
        )


def ensure_ffmpeg():
    if not cmd_exists("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is not installed. It is required for audio extraction.\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  macOS: brew install ffmpeg"
        )


def ensure_faster_whisper():
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed.\n"
            "  Install: pip install video-digestor[transcribe]\n"
            "  Or: pip install faster-whisper"
        )


# ---------------------------------------------------------------------------
# Path / output helpers
# ---------------------------------------------------------------------------

def sanitize_dirname(name: str) -> str:
    """Convert a string to a safe directory name."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name)
    name = name.strip("_. ")
    return name[:120]


def setup_output_dir(title: str, base_dir: Path | None = None) -> Path:
    """Create and return the output directory for a video.

    Directory layout: {base_dir}/{sanitized_title}/
    """
    base = base_dir or Path("./output")
    dirname = sanitize_dirname(title) or "video"
    out = base / dirname
    out.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", out)
    return out


def write_metadata(out_dir: Path, meta: dict) -> Path:
    """Write metadata.json to the output directory."""
    path = out_dir / "metadata.json"
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def split_text(text: str, max_chars: int = 8000) -> list[str]:
    """Split text into chunks of at most max_chars, trying to break at sentence boundaries."""
    chunks = []
    while len(text) > max_chars:
        split_at = text.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text.strip():
        chunks.append(text.strip())
    return chunks
