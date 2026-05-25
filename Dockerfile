FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  curl build-essential \
  ca-certificates && \
  curl -LsSf https://astral.sh/uv/install.sh | sh && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin/:${PATH}"

COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

