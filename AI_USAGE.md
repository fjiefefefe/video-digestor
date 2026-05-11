# video-digestor — AI 使用说明

你是 AI 助手，以下教你如何使用 `video-digestor` 帮用户处理视频内容。

## 是什么

一个本地 CLI 工具，输入视频 URL → 输出结构化 Markdown 笔记。流程：

```
inspect → 有字幕？→ 直接下载 → summarize → summary.md
                   → 无字幕？→ 下载音频 → transcribe → summarize → summary.md
```

## 安装（帮用户装）

```bash
cd /path/to/video-digestor
pip install -e ".[transcribe]"

# 系统依赖
sudo apt install -y ffmpeg          # Linux
brew install ffmpeg                 # macOS
```

### 可选：YouTube JS 运行时

```bash
curl -fsSL https://deno.land/install.sh | sh
# 或直接下载二进制
# https://github.com/denoland/deno/releases
```

## 环境变量

```bash
export DEEPSEEK_API_KEY="sk-xxxx"    # AI 总结用（必需，默认 provider）
export HF_ENDPOINT="https://hf-mirror.com"  # 国内加速模型下载（可选）
```

## 六个命令

### `inspect` — 快速看视频能不能处理

```bash
video-digestor inspect "URL"
# 输出：标题、时长、有无字幕、能否下音频
# 判断依据：字幕有 → 秒级完成；无 → 需转写（分钟级）
```

### `fetch` — 只拿字幕/音频，不总结

```bash
video-digestor fetch "URL" --lang zh,en
# --audio-only  跳过字幕，直接下音频
# 输出目录：{项目根}/output/{标题}/
```

### `transcribe` — 音频转文字

```bash
video-digestor transcribe audio.mp3 -m medium -l zh
# -m  模型：tiny(快)/small/medium/large-v3(准)
# -l  语言代码，中文 zh 大幅提高精度
# -d  设备：cuda(默认)/cpu
# -b  搜索宽度 1-20，越大越准越慢
```

### `summarize` — 生成 Markdown 笔记

```bash
video-digestor summarize transcript.txt -t "视频标题"
# --provider openai  默认，用 DeepSeek AI 总结
# --provider local   不用 AI，只排版
# --provider none    纯原文
```

### `run` — 一键全流程（最常用）

```bash
video-digestor run "URL" -m medium -l zh
# 自动判断：有字幕跳过转写，无字幕走全流程
# --skip-summary  只拿字幕/转写，不总结
```

### `cleanup` — 清理文件

```bash
video-digestor cleanup --all         # 清 output
video-digestor cleanup --all -k      # 只删 mp3，保留文本
video-digestor cleanup --all -n      # 预览不真删
```

## 常见场景

### 场景 1：用户发来 YouTube 链接

```bash
# 默认用 Firefox cookie + DeepSeek 总结，GPU 转写
video-digestor run "https://www.youtube.com/watch?v=xxxxx" -m medium -l zh

# YouTube 反爬 → 先检查是否装了 deno
# 没有的话帮装：curl -fsSL https://deno.land/install.sh | sh
```

### 场景 2：用户发来 B站链接

```bash
# 自动用 Firefox cookie 拿 AI 字幕（如果用户浏览器登录了B站）
video-digestor run "https://www.bilibili.com/video/BVxxxxxx" -m medium -l zh

# 如果抓不到字幕 → 提示用户浏览器登录 bilibili.com
# 然后重试，会自动走转写流程
```

### 场景 3：用户想只看不总结

```bash
video-digestor run "URL" --skip-summary
# 输出：raw_subtitle.srt + transcript.txt
# 没有 summary.md
```

### 场景 4：用户已有音频文件

```bash
video-digestor transcribe ~/Downloads/lecture.mp3 -m medium -l zh
# 然后
video-digestor summarize ./output/lecture/transcript.txt -t "讲座标题"
```

### 场景 5：不用 AI，只要排版

```bash
video-digestor run "URL" --provider local
# 不调用 API，生成结构化 Markdown 但不提炼内容
```

## 输出结构

```
output/{视频标题}/
├── metadata.json       # 视频信息
├── raw_subtitle.srt    # 字幕 SRT 格式
├── transcript.txt      # 带时间戳全文（如果有字幕，就是 SRT 原文）
└── summary.md          # AI 生成的 7 段式笔记
```

## 判断决策树

作为 AI，收到用户视频链接后应该：

1. 看 URL 域名判断平台（YouTube 需 deno，B站需 cookie）
2. `inspect` 看有没有字幕 → 有字幕几秒搞定，没字幕告诉用户要等转写
3. 推荐参数：中文视频 `-l zh -m medium`，英文 `-l en -m small`
4. 用户没 GPU 时加 `-d cpu`
5. DeepSeek key 没配时先帮配：`export DEEPSEEK_API_KEY="sk-xxxx"`

## 错误处理速查

| 错误 | 原因 | 解法 |
|------|------|------|
| `Sign in to confirm you're not a bot` | YouTube 反爬 | 装 deno |
| `ffmpeg is not installed` | 缺系统依赖 | `sudo apt install ffmpeg` |
| `No API key found` | 没配 DeepSeek key | `export DEEPSEEK_API_KEY="sk-xxxx"` |
| B站字幕 未找到任何字幕 | 没登录 B站 | 用户浏览器登录 bilibili.com 后重试 |
| 转写很慢 | 在用 CPU | 加 `-d cuda`（需要 NVIDIA GPU + CUDA Toolkit） |
| faster-whisper not installed | 没装可选依赖 | `pip install faster-whisper` |
