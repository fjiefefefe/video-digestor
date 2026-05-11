"""video-digestor CLI — 视频内容抓取与总结工具"""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel

from video_digestor import __version__
from video_digestor.utils import (
    console,
    log,
    ensure_ytdlp,
    setup_output_dir,
    write_metadata,
)
from video_digestor.downloader import (
    get_video_info,
    download_subtitles,
    download_audio,
    has_audio_formats,
)
from video_digestor.summarizer import (
    NoAISummarizer,
    LocalPromptSummarizer,
    OpenAISummarizer,
)

app = typer.Typer(
    name="video-digestor",
    help="本地视频内容抓取与总结工具",
    add_completion=False,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _resolve_output_dir(title: str, output: Optional[Path]) -> Path:
    return setup_output_dir(title, output)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

@app.command()
def inspect(
    url: str = typer.Argument(..., help="视频 URL"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录（默认 ./output）"),
    cookies_from_browser: Optional[str] = typer.Option(None, "--cookies-from-browser", help="从浏览器读取 cookie，如 chrome/firefox/edge"),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies", help="cookies.txt 文件路径"),
    js_runtimes: Optional[str] = typer.Option("deno", "--js-runtimes", help="JS 运行时，如 deno/node (默认 deno)"),
):
    """查看视频元数据：标题、可用字幕、音频格式等。"""
    info = get_video_info(url, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)

    console.print(Panel.fit(f"[bold cyan]{info['title']}[/bold cyan]", title="视频信息"))
    console.print(f"  ID: {info['id']}")
    console.print(f"  时长: {info['duration']}s")
    console.print(f"  发布者: {info['uploader']}")

    if info["subtitles"]:
        console.print(f"  [green]人工字幕:[/green] {', '.join(info['subtitles'])}")
    else:
        console.print("  [yellow]人工字幕: 无[/yellow]")

    if info["automatic_captions"]:
        console.print(f"  [green]自动字幕:[/green] {', '.join(info['automatic_captions'])}")
    else:
        console.print("  [yellow]自动字幕: 无[/yellow]")

    console.print(f"  可提取音频: {'[green]是[/green]' if has_audio_formats(info) else '[yellow]否[/yellow]'}")

    out_dir = _resolve_output_dir(info["title"], output)
    write_metadata(out_dir, info)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

@app.command()
def fetch(
    url: str = typer.Argument(..., help="视频 URL"),
    lang: str = typer.Option("zh,en", "--lang", "-l", help="字幕语言偏好（逗号分隔）"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录（默认 ./output）"),
    audio_only: bool = typer.Option(False, "--audio-only", "-a", help="跳过字幕，直接抽取音频"),
    cookies_from_browser: Optional[str] = typer.Option(None, "--cookies-from-browser", help="从浏览器读取 cookie，如 chrome/firefox/edge"),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies", help="cookies.txt 文件路径"),
    js_runtimes: Optional[str] = typer.Option("deno", "--js-runtimes", help="JS 运行时，如 deno/node (默认 deno)"),
):
    """下载字幕或音频。优先字幕，无字幕时自动抽取音频。"""
    info = get_video_info(url, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)
    out_dir = _resolve_output_dir(info["title"], output)
    write_metadata(out_dir, info)

    langs = [l.strip() for l in lang.split(",") if l.strip()]
    srt_path = None

    if not audio_only:
        srt_path = download_subtitles(url, out_dir, langs, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)

    if srt_path:
        text = srt_path.read_text(encoding="utf-8")

        transcript_path = out_dir / "transcript.txt"
        transcript_path.write_text(text, encoding="utf-8")
        log.info("Copied subtitle text to transcript.txt")
    else:
        if audio_only:
            log.info("--audio-only 模式：跳过字幕，直接下载音频")
        else:
            log.info("No subtitles available. Falling back to audio download.")

        audio_path = download_audio(url, out_dir, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)
        if audio_path:
            log.info("Audio saved. Run 'video-digestor transcribe %s' to transcribe.", audio_path)
        else:
            log.warning("Failed to download audio.")


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------

@app.command()
def transcribe(
    path: Path = typer.Argument(..., help="音频文件路径"),
    model: str = typer.Option("small", "--model", "-m", help="模型大小: tiny/small/medium/large-v3"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="语言代码，如 zh/en"),
    device: str = typer.Option("cuda", "--device", "-d", help="推理设备: cpu / cuda"),
    compute_type: str = typer.Option("int8", "--compute-type", "-c", help="计算精度: int8 / float16"),
    beam_size: int = typer.Option(5, "--beam-size", "-b", help="搜索宽度 (1-20)，越大精度越高但越慢"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录（默认 ./output）"),
):
    """用 faster-whisper 本地转写音频为字幕和文本。"""
    from video_digestor.transcriber import transcribe as do_transcribe

    if not path.exists():
        raise typer.BadParameter(f"文件不存在: {path}")

    out_dir = _resolve_output_dir(path.stem, output)
    do_transcribe(path, out_dir, model_size=model, language=language,
                  device=device, compute_type=compute_type, beam_size=beam_size)
    log.info("转写完成。运行 'video-digestor summarize %s' 生成笔记。",
             out_dir / "transcript.txt")


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

@app.command()
def summarize(
    transcript: Path = typer.Argument(..., help="transcript.txt 路径"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录（默认 transcript 所在目录）"),
    provider: str = typer.Option("openai", "--provider", "-p", help="总结引擎: none / local / openai"),
    prompt: Optional[Path] = typer.Option(None, "--prompt", help="自定义 prompt 文件（provider=local 时使用）"),
    title: str = typer.Option("视频笔记", "--title", "-t", help="视频标题"),
):
    """将 transcript 总结为 Markdown 笔记。"""
    if not transcript.exists():
        raise typer.BadParameter(f"File not found: {transcript}")

    out_dir = output or transcript.parent

    if provider == "none":
        s = NoAISummarizer()
    elif provider == "local":
        s = LocalPromptSummarizer(prompt_path=prompt)
    elif provider == "openai":
        s = OpenAISummarizer()
    else:
        raise typer.BadParameter(f"Unknown provider: {provider}. Use: none / local / openai")

    result = s.summarize(transcript, out_dir, title)
    log.info("Summary saved: %s", result)


# ---------------------------------------------------------------------------
# run — 一键管道
# ---------------------------------------------------------------------------

@app.command()
def run(
    url: str = typer.Argument(..., help="视频 URL"),
    lang: str = typer.Option("zh,en", "--lang", "-l", help="字幕语言偏好（逗号分隔）"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录（默认 ./output）"),
    model: str = typer.Option("small", "--model", "-m", help="faster-whisper 模型大小"),
    language: Optional[str] = typer.Option(None, "--language", help="转写语言代码"),
    device: str = typer.Option("cuda", "--device", "-d", help="推理设备: cpu / cuda"),
    compute_type: str = typer.Option("int8", "--compute-type", "-c", help="计算精度: int8 / float16"),
    beam_size: int = typer.Option(5, "--beam-size", "-b", help="搜索宽度 (1-20)"),
    provider: str = typer.Option("openai", "--provider", "-p", help="总结引擎: none / local / openai"),
    skip_summary: bool = typer.Option(False, "--skip-summary", help="跳过总结步骤"),
    cookies_from_browser: Optional[str] = typer.Option(None, "--cookies-from-browser", help="从浏览器读取 cookie，如 chrome/firefox/edge"),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies", help="cookies.txt 文件路径"),
    js_runtimes: Optional[str] = typer.Option("deno", "--js-runtimes", help="JS 运行时，如 deno/node (默认 deno)"),
):
    """一键完成: inspect → fetch → (必要时 transcribe) → summarize。"""
    info = get_video_info(url, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)
    out_dir = _resolve_output_dir(info["title"], output)
    write_metadata(out_dir, info)

    console.print(Panel.fit(f"[bold cyan]{info['title']}[/bold cyan]", title="处理中"))

    langs = [l.strip() for l in lang.split(",") if l.strip()]

    srt_path = download_subtitles(url, out_dir, langs, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)

    transcript_path: Path | None = None

    if srt_path:
        text = srt_path.read_text(encoding="utf-8")
        transcript_path = out_dir / "transcript.txt"
        transcript_path.write_text(text, encoding="utf-8")
        log.info("Subtitle saved as transcript.")
    else:
        log.info("No subtitles. Extracting audio...")
        audio_path = download_audio(url, out_dir, cookies_from_browser=cookies_from_browser, cookies_file=cookies_file, js_runtimes=js_runtimes)
        if not audio_path:
            log.error("Cannot proceed: audio download failed.")
            raise typer.Exit(code=1)

        log.info("Transcribing audio...")
        try:
            from video_digestor.transcriber import transcribe as do_transcribe
            srt_out, transcript_path = do_transcribe(
                audio_path, out_dir, model_size=model, language=language,
                device=device, compute_type=compute_type, beam_size=beam_size
            )
        except (ImportError, RuntimeError) as e:
            log.error("Transcription failed: %s", e)
            log.error(
                "Install faster-whisper and run manually:\n"
                "  pip install video-digestor[transcribe]\n"
                "  video-digestor transcribe %s", audio_path
            )
            raise typer.Exit(code=1)

    if skip_summary:
        log.info("Skipping summary generation.")
        return

    if not transcript_path:
        log.error("No transcript available for summarization.")
        raise typer.Exit(code=1)

    if provider == "none":
        s = NoAISummarizer()
    elif provider == "local":
        s = LocalPromptSummarizer()
    elif provider == "openai":
        s = OpenAISummarizer()
    else:
        raise typer.BadParameter(f"Unknown provider: {provider}")

    s.summarize(transcript_path, out_dir, info["title"])
    console.print(f"\n[green]Done![/green] Output: {out_dir}")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

@app.command()
def version():
    """显示版本信息。"""
    console.print(f"video-digestor v{__version__}")


# ---------------------------------------------------------------------------
# cleanup — 清理缓存和大文件
# ---------------------------------------------------------------------------

@app.command()
def cleanup(
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="清理指定输出目录（默认 ./output）"),
    all_output: bool = typer.Option(False, "--all", help="清理所有 ./output 目录"),
    keep_text: bool = typer.Option(False, "--keep-text", "-k", help="保留 srt/txt/md，只删音频"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="只列出将删除的文件，不实际删除"),
):
    """清理下载的音频文件和输出目录，释放磁盘空间。"""
    import shutil

    base = output_dir or Path("./output")
    total_size = 0
    files_removed = 0

    if all_output or output_dir:
        targets = [base] if output_dir else sorted(base.iterdir()) if base.exists() else []
        for target in targets:
            if not target.exists():
                continue
            for f in target.rglob("*"):
                if f.is_file():
                    size = f.stat().st_size
                    if keep_text and f.suffix in (".srt", ".txt", ".md", ".json"):
                        continue
                    total_size += size
                    if not dry_run:
                        f.unlink()
                    files_removed += 1
                    log.info("%s %s (%s)", "  会删除" if dry_run else "已删除", f, _fmt_size(size))
            if not keep_text and not dry_run and target.exists():
                try:
                    target.rmdir()
                except OSError:
                    pass

    size_str = _fmt_size(total_size)
    if dry_run:
        console.print(f"\n[yellow]将删除 {files_removed} 个文件，释放 {size_str}[/yellow]")
    else:
        console.print(f"\n[green]已删除 {files_removed} 个文件，释放 {size_str}[/green]")


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


if __name__ == "__main__":
    app()
