# Based on https://depot.dev/docs/container-builds/optimal-dockerfiles/python-uv-dockerfile
# This is a multistage setup.

ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.11.3

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# Compile Stage
FROM python:${PYTHON_VERSION}-slim AS BUILD

COPY --from=uv /uv /uvx /bin

RUN mkdir /markovbot
WORKDIR /markovbot

# Compiles the bytecode and copies files instead of symlinking them
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# This copies the project config and installs the dependencies separately
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# This copies the full app (.py files and whatnot) and installs the project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime Stage
FROM python:${PYTHON_VERSION} as runtime

ENV PATH="/markovbot/.venv/bin:$PATH"

# We're essentially setting up the user and the correct permissions

RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -d /markovbot -s /bin/false appuser

WORKDIR /markovbot

COPY --from=build --chown=appuser:appgroup /markovbot .

USER appuser

ENTRYPOINT ["python3", "markovbot.py"]
