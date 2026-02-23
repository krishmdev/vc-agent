# Image for the offline e2e. Setup runs in it with network; the e2e runs in it with --network none.
FROM mcr.microsoft.com/playwright:v1.63.0-noble
COPY --from=ghcr.io/astral-sh/uv:0.9.28 /uv /uvx /usr/local/bin/
RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*
# Keep uv's Python, caches and browsers inside the mounted workspace so both phases share them.
ENV UV_PYTHON_INSTALL_DIR=/work/.uv-python \
    UV_CACHE_DIR=/work/.uv-cache \
    npm_config_cache=/work/.npm \
    CI=1
WORKDIR /work
