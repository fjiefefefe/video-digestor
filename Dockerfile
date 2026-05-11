FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# deno (YouTube JS challenge solver)
RUN curl -fsSL "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip" -o /tmp/deno.zip \
    && unzip -o /tmp/deno.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/deno \
    && rm /tmp/deno.zip

WORKDIR /app
COPY . /app

RUN pip install -e ".[transcribe]"

ENV HF_HOME=/app/.cache/huggingface

VOLUME ["/app/output", "/app/.cache"]

ENTRYPOINT ["video-digestor"]
