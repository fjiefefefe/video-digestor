import logging
from pathlib import Path

from video_digestor.utils import ensure_faster_whisper

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model size helpers
# ---------------------------------------------------------------------------

MODEL_SIZES = {
    "tiny": "tiny",
    "small": "small",
    "medium": "medium",
    "large-v3": "large-v3",
}


def resolve_model_size(size: str) -> str:
    """Resolve shorthand model size names to full faster-whisper model names."""
    key = size.lower()
    if key in MODEL_SIZES:
        return MODEL_SIZES[key]
    raise ValueError(
        f"Unknown model size: {size!r}. Available: {list(MODEL_SIZES.keys())}"
    )


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe(
    audio_path: Path,
    out_dir: Path,
    model_size: str = "small",
    language: str | None = None,
    device: str = "cuda",
    compute_type: str = "int8",
    beam_size: int = 5,
) -> tuple[Path, Path]:
    """Transcribe audio using faster-whisper.

    Returns:
        (srt_path, txt_path)
    """
    ensure_faster_whisper()
    from faster_whisper import WhisperModel

    model_name = resolve_model_size(model_size)
    log.info("Loading faster-whisper model: %s (device=%s, compute=%s)", model_name, device, compute_type)
    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    lang_kwargs = {"language": language} if language else {}
    log.info("Transcribing %s ...", audio_path)
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=beam_size,
        vad_filter=True,
        **lang_kwargs,
    )
    log.info("Detected language: %s (prob=%.2f)", info.language, info.language_probability)

    srt_path = out_dir / "raw_subtitle.srt"
    txt_path = out_dir / "transcript.txt"

    srt_lines = []
    txt_lines = []
    idx = 1

    for seg in segments:
        start = seg.start
        end = seg.end
        text = seg.text.strip()

        srt_lines.append(f"{idx}")
        srt_lines.append(f"{_fmt_timestamp(start)} --> {_fmt_timestamp(end)}")
        srt_lines.append(text)
        srt_lines.append("")

        txt_lines.append(f"[{_fmt_timestamp(start)}] {text}")
        idx += 1

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

    log.info("Saved SRT: %s", srt_path)
    log.info("Saved TXT: %s", txt_path)
    return srt_path, txt_path


def _fmt_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
