# The dashboard's images (score/dashboard). Build from the repository root:
#   docker build -f score/dashboard/Dockerfile --target hosted -t score-dashboard:hosted .
# hosted: only the dashboard group (Django, FastAPI, uvicorn), never numpy or usd-core; local: the full project, a
# read-only reader of a mounted store. Both run as a non-root user behind a trusted proxy (no password sign-in in a
# container), uvicorn without proxy headers, one worker, /data a volume.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SCORE_DASHBOARD_HOME=/data SCORE_BIND=0.0.0.0:8780
RUN pip install --no-cache-dir uv==0.8.22 && useradd --create-home --uid 10001 score && mkdir /data && chown score /data
WORKDIR /app

FROM base AS hosted
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --only-group dashboard --no-hashes -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt
COPY score/__init__.py score/__init__.py
COPY score/dashboard score/dashboard
COPY design/tokens/colours.css design/tokens/scale.css design/tokens/
COPY design/fonts design/fonts
COPY tools/review/viewer/viewer.html tools/review/viewer/viewer.html
COPY data/films data/films
# The commit this image is built at, told by /healthz (the pin the conductor's checkout follows): --build-arg
# SCORE_COMMIT=<sha>; a hosting repository that pins it as an ARG sets this ENV from it the same way.
ARG SCORE_COMMIT=""
ENV SCORE_DASHBOARD_MODE=hosted SCORE_STORE_WRITABLE=0 SCORE_COMMIT=${SCORE_COMMIT}
USER score
VOLUME /data
EXPOSE 8780
CMD ["python", "-m", "score.dashboard", "serve"]

FROM base AS local
COPY . .
RUN uv sync --frozen --group dashboard && chown -R score /app/.venv
ENV SCORE_DASHBOARD_MODE=local SCORE_STORE_WRITABLE=0 PATH=/app/.venv/bin:$PATH
USER score
VOLUME /data
EXPOSE 8780
CMD ["python", "-m", "score.dashboard", "serve"]
