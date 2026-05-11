# video-digestor — AI 使用说明

你是 AI 助手，以下教你如何使用 `video-digestor` 帮用户处理视频内容。

## 是什么

一个本地 CLI 工具，输入视频 URL → 输出结构化 Markdown 笔记。流程：

```
inspect → 有字幕？→ 直接下载 → summarize → summary.md + article.md(自动)
                   → 无字幕？→ 下载音频 → transcribe → summarize → summary.md + article.md(自动)
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

# 同时生成阅读体文章（自动判断风格）
video-digestor summarize transcript.txt --with-article -t "标题"
# --book    强制保留原文、出版书风格排版
# --narrate 强制 AI 转述改写
```

**文章模式说明：**

| 模式 | 说明 |
|------|------|
| `auto` (默认) | AI 先判断文字是口语还是书面稿。口语 → 转述改写，书面稿 → 保留原文排版 |
| `--book` | 保留原文措辞和叙事顺序，去口语词、分章节、加标点。适合纪录片/旁白 |
| `--narrate` | AI 转述为"视频中提到...作者认为..."的第三人称流畅文章。适合播客/聊天 |

### `run` — 一键全流程（最常用）

```bash
video-digestor run "URL" -m medium -l zh
# 自动判断：有字幕跳过转写，无字幕走全流程
# 默认自动生成 article.md（AI 判断口语/书稿风格）
# --book    强制书稿排版风格
# --narrate 强制转述改写风格
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

### 场景 2.5：用户发来抖音链接

```bash
# 抖音需要 Chrome 登录 douyin.com 后才可用
video-digestor run "https://www.douyin.com/video/xxxxx" --cookies-from-browser chrome -m medium -l zh

# 也支持精选页链接
video-digestor run "https://www.douyin.com/jingxuan?modal_id=xxxxx" --cookies-from-browser chrome

# 抖音没有字幕，自动走：API 取描述 → 下载音频 → faster-whisper 转写 → AI 总结
# 抖音内置 ABogus 签名，不依赖 yt-dlp
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

### 场景 5：不要 AI 总结，只要排版

```bash
video-digestor run "URL" --provider local
# 不调用 API，生成结构化 Markdown 但不提炼内容
```

### 场景 6：高质量纪录片文案，要保留原文出书稿

```bash
video-digestor run "URL" --book
# 或自动判断：
video-digestor run "URL"
# AI 会自动识别旁白风格 → 走书稿排版模式，保留原文措辞
```

### 场景 7：播客聊天视频，要流畅阅读体

```bash
video-digestor run "URL" --narrate
# 或自动判断：
video-digestor run "URL"  
# AI 自动识别口语风格 → 走转述改写模式
```

## 输出结构

```
output/{视频标题}/
├── metadata.json       # 视频信息
├── raw_subtitle.srt    # 字幕 SRT 格式
├── transcript.txt      # 带时间戳全文（如果有字幕，就是 SRT 原文）
├── summary.md          # AI 生成的 7 段式笔记
└── article.md          # 阅读体文章（自动判断风格）
```

`article.md` 根据文字类型自动选择：
- **口语** → AI 转述改写体（"视频中提到...作者认为..."）
- **书面稿** → 出版编辑体（保留原文、分章节、去口语）

## 判断决策树

作为 AI，收到用户视频链接后应该：

1. 看 URL 域名判断平台（YouTube 需 deno，B站需 cookie，抖音需 Chrome cookie）
2. `inspect` 看有没有字幕 → 有字幕几秒搞定，没字幕告诉用户要等转写
3. 推荐参数：中文视频 `-l zh -m medium`，英文 `-l en -m small`
4. 用户没 GPU 时加 `-d cpu`
5. DeepSeek key 没配时先帮配：`export DEEPSEEK_API_KEY="sk-xxxx"`
6. 抖音 URL 先检查 `--cookies-from-browser chrome`，用户没登录 douyin.com 时提示登录

## 错误处理速查

| 错误 | 原因 | 解法 |
|------|------|------|
| `Sign in to confirm you're not a bot` | YouTube 反爬 | 装 deno |
| `ffmpeg is not installed` | 缺系统依赖 | `sudo apt install ffmpeg` |
| `No API key found` | 没配 DeepSeek key | `export DEEPSEEK_API_KEY="sk-xxxx"` |
| B站字幕 未找到任何字幕 | 没登录 B站 | 用户浏览器登录 bilibili.com 后重试 |
| 转写很慢 | 在用 CPU | 加 `-d cuda`（需要 NVIDIA GPU + CUDA Toolkit） |
| faster-whisper not installed | 没装可选依赖 | `pip install faster-whisper` |
| 抖音 API 返回空 | 没登录 douyin.com 或 cookie 过期 | 浏览器登录 douyin.com 后重试 |
| gmssl 报错 | 没装 gmssl | `pip install gmssl` |
