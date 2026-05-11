"""Summarizer: 可插拔的总结模块。

支持三种模式:
  - none:    不调用 AI，仅输出 clean transcript 和基本 Markdown 骨架
  - local:   使用本地 prompt 模板，将 transcript 按块处理后保存到 markdown
  - openai:  调用 OpenAI-compatible API (默认指向 DeepSeek)
"""

import logging
import os
from pathlib import Path
from abc import ABC, abstractmethod

from video_digestor.utils import split_text

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseSummarizer(ABC):
    @abstractmethod
    def summarize(self, transcript_path: Path, out_dir: Path, video_title: str) -> Path:
        """Generate summary.md in out_dir. Returns the path."""
        ...


# ---------------------------------------------------------------------------
# No-AI summarizer
# ---------------------------------------------------------------------------

class NoAISummarizer(BaseSummarizer):
    """Output a clean transcript-only Markdown. No AI involved."""

    def summarize(self, transcript_path: Path, out_dir: Path, video_title: str) -> Path:
        transcript = transcript_path.read_text(encoding="utf-8")

        summary_md = out_dir / "summary.md"
        content = f"""# {video_title}

## 转写文本

> 以下为视频转写全文（未经过 AI 总结）

{transcript}
"""
        summary_md.write_text(content, encoding="utf-8")
        log.info("Saved no-AI summary: %s", summary_md)
        return summary_md


# ---------------------------------------------------------------------------
# Local prompt summarizer
# ---------------------------------------------------------------------------

class LocalPromptSummarizer(BaseSummarizer):
    """Use a local prompt template + chunking to produce a structured summary.

    This works without any AI API — it structures the transcript into the
    required Markdown sections by using the prompt as a formatting guide
    and chunking the transcript by time segments.
    """

    def __init__(self, prompt_path: Path | None = None):
        self.prompt_path = prompt_path or PROMPTS_DIR / "default_summary.md"
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_path}")

    def summarize(self, transcript_path: Path, out_dir: Path, video_title: str) -> Path:
        transcript = transcript_path.read_text(encoding="utf-8")
        prompt_template = self.prompt_path.read_text(encoding="utf-8")

        chunks = split_text(transcript, max_chars=8000)

        summary_md = out_dir / "summary.md"
        with open(summary_md, "w", encoding="utf-8") as f:
            f.write(f"# {video_title}\n\n")
            f.write("## 一句话结论\n\n> 以下为本地模板总结（未调用 AI），请查看下方转写内容自行判断。\n\n")
            f.write("## 转写文本\n\n")
            for i, chunk in enumerate(chunks, 1):
                if len(chunks) > 1:
                    f.write(f"### 第 {i} 部分\n\n")
                f.write(f"{chunk}\n\n")

            f.write("---\n\n")
            f.write("## 总结提示\n\n")
            f.write(f"{prompt_template.format(title=video_title, transcript='[见上方转写文本]')}\n")

        log.info("Saved local-prompt summary: %s", summary_md)
        return summary_md


# ---------------------------------------------------------------------------
# OpenAI-compatible summarizer (默认指向 DeepSeek)
# ---------------------------------------------------------------------------

class OpenAISummarizer(BaseSummarizer):
    """Call an OpenAI-compatible chat completion API.

    Defaults to DeepSeek (api.deepseek.com).
    Set DEEPSEEK_API_KEY or OPENAI_API_KEY env var to authenticate.
    Override via OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL env vars.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "deepseek-chat")

    def summarize(self, transcript_path: Path, out_dir: Path, video_title: str) -> Path:
        if not self.api_key:
            raise RuntimeError(
                "No API key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable."
            )

        from openai import OpenAI

        transcript = transcript_path.read_text(encoding="utf-8")
        prompt_path = PROMPTS_DIR / "default_summary.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(title=video_title, transcript=transcript)

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        log.info("Calling %s model %s ...", self.base_url, self.model)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的视频内容总结助手。请严格按照用户要求的 Markdown 格式输出。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        content = response.choices[0].message.content

        summary_md = out_dir / "summary.md"
        summary_md.write_text(content, encoding="utf-8")
        log.info("Saved AI summary: %s", summary_md)
        return summary_md
