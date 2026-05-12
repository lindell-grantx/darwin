FROM python:3.12-slim

WORKDIR /app

# System deps for any native packages (motor, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed for pip install -e first (layer caching)
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -r requirements.txt

# Copy scripts and tests after deps (changes more often)
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Default to supervisor; override in compose
CMD ["python", "scripts/run_all.py"]
