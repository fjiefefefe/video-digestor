# video-digestor

把视频链接/文件转成可读 Markdown 笔记。支持 YouTube、Bilibili 等主流平台。

## 工作流程

```
视频 URL → 优先下载字幕 → 无字幕则抽音频 → 本地转写(faster-whisper) → AI 总结(可选)
```

## 安装

```bash
# 1. 克隆
git clone https://github.com/fjiefefefe/video-digestor.git
cd video-digestor

# 2. 基础安装
pip install -e .

# 3. 含语音转写（需要 faster-whisper，模型首次运行自动下载）
pip install -e ".[transcribe]"

# 4. 系统依赖
sudo apt install ffmpeg              # Linux
brew install ffmpeg                  # macOS

# 5. YouTube 需要 JS 运行时（推荐 deno）
curl -fsSL https://deno.land/install.sh | sh
# 或从 GitHub 直接下载
# https://github.com/denoland/deno/releases
```

## 快速开始

```bash
# 查看视频信息（标题、字幕、音频格式）
video-digestor inspect "https://www.youtube.com/watch?v=xxxxx"

# 下载字幕，无字幕则抽取音频
video-digestor fetch "https://www.youtube.com/watch?v=xxxxx" --lang zh,en

# 本地转写音频（首次运行会自动下载模型）
video-digestor transcribe audio.mp3 -m medium -l zh

# 生成 Markdown 笔记
video-digestor summarize transcript.txt --provider local

# 一键全流程
video-digestor run "https://www.bilibili.com/video/BVxxxxxx" -m medium -l zh
```

## 命令参考

### `inspect` — 查看视频信息

```bash
video-digestor inspect "URL"
```

输出：标题、时长、发布者、可用字幕语言、是否可提取音频。

### `fetch` — 下载字幕或音频

```bash
video-digestor fetch "URL" [--lang zh,en] [--audio-only]
```

优先尝试人工字幕 → 自动字幕 → 音频下载。音频下载需要 ffmpeg。

### `transcribe` — 语音转写

```bash
video-digestor transcribe audio.mp3 [OPTIONS]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-m, --model` | `medium` | 模型大小：tiny / small / medium / large-v3 |
| `-l, --language` | 自动检测 | 指定语言代码如 `zh`，大幅提高精度 |
| `-d, --device` | `cuda` | 推理设备：cpu / cuda |
| `-c, --compute-type` | `int8` | 计算精度：int8 / float16 |
| `-b, --beam-size` | `5` | 搜索宽度 (1-20)，越大精度越高但越慢 |

**模型大小参考：**

| 模型 | 大小 | 内存 | 适合场景 |
|------|------|------|----------|
| `tiny` | ~150MB | ~1GB | 快速试听 |
| `small` | ~500MB | ~2GB | 日常使用 |
| `medium` | ~1.5GB | ~5GB | 较高精度 |
| `large-v3` | ~3GB | ~10GB | 最高精度 |

**提高中文转写精度：**

```bash
# 指定语言 + 大模型 + float16 + 加大搜索宽度
video-digestor transcribe audio.mp3 -m large-v3 -l zh -c float16 -b 10
```

### `summarize` — 生成 Markdown 笔记

```bash
video-digestor summarize transcript.txt [--provider none|local|openai]
```

| 提供者 | 说明 |
|--------|------|
| `none` | 不调用 AI，仅输出完整 transcript |
| `local` (默认) | 结构化排版，不调用 API |
| `openai` | 调用 AI 生成结构化笔记 |

**AI 总结使用 DeepSeek：**

```bash
export DEEPSEEK_API_KEY="sk-xxxxx"
video-digestor summarize transcript.txt --provider openai --title "视频标题"
```

**自定义 AI 端点：**

```bash
export OPENAI_BASE_URL="https://your-api.com/v1"
export OPENAI_API_KEY="sk-xxxxx"
export OPENAI_MODEL="your-model"
```

### `run` — 一键全流程

```bash
video-digestor run "URL" [OPTIONS]
```

包含 `inspect` → `fetch` → `transcribe`（如需）→ `summarize` 全部步骤。

### `cleanup` — 清理文件

```bash
video-digestor cleanup --all --dry-run   # 预览
video-digestor cleanup --all             # 清理所有输出目录
video-digestor cleanup -k                # 只删音频，保留文本
```

## YouTube/B站 访问

### YouTube Cookie 认证

YouTube 可能要求登录验证，通过浏览器 cookie 解决：

```bash
# 从浏览器读取（推荐 Firefox）
video-digestor run "URL" --cookies-from-browser firefox

# 也支持 Chrome / Edge
video-digestor run "URL" --cookies-from-browser chrome

# 或导出 cookies.txt
video-digestor run "URL" --cookies ./cookies.txt
```

### JS 运行时

YouTube 需要 JS 运行时解 challenge，默认自动下载 deno 脚本。如果没有 deno：

```bash
curl -fsSL https://deno.land/install.sh | sh
# 加入 PATH
export PATH="$HOME/.local/bin:$PATH"

# 如果只有 node：
video-digestor run "URL" --js-runtimes node
```

也可在 `~/.config/yt-dlp/config` 中配置 `--cookies-from-browser` 和 `--js-runtimes` 作为全局默认。

## 输出目录结构

```
output/
└── 视频标题/
    ├── metadata.json       # 视频元信息
    ├── raw_subtitle.srt    # 字幕（SRT 格式）
    ├── transcript.txt      # 转写文本（带时间戳）
    └── summary.md          # Markdown 笔记
```

`summary.md` 包含 7 个标准化段落：一句话结论、核心内容、可执行步骤、命令/代码、坑点、时间戳索引。

## 常见问题

**Q: yt-dlp 报错或需要更新？**
```bash
pip install -U yt-dlp
```

**Q: faster-whisper 模型下载慢？**
```bash
export HF_ENDPOINT=https://hf-mirror.com   # HuggingFace 镜像
```

**Q: 显存不够 / 想用 CPU？**
```bash
video-digestor transcribe audio.mp3 -d cpu -m small
```

**Q: YouTube 报 "Sign in to confirm you're not a bot"？**
```bash
video-digestor run "URL" --cookies-from-browser firefox
```

## 依赖

| 类型 | 包 | 说明 |
|------|-----|------|
| Python | typer, rich, yt-dlp, openai, srt | 核心依赖 |
| Python (可选) | faster-whisper | 本地语音转写 |
| 系统 | ffmpeg | 音频提取 |
| 系统 (可选) | deno | YouTube JS challenge 解算 |

## License

MIT
