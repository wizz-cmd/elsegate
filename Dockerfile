FROM python:3.12-slim

# Git is needed if claude_code backend uses Claude Code CLI
# (which requires git for session management)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY elsegate/ ./elsegate/

EXPOSE 11434

CMD ["python", "-m", "uvicorn", "elsegate.server:app", "--host", "0.0.0.0", "--port", "11434"]
