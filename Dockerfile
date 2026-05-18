# Build stage
FROM python:3.13-slim@sha256:dc1546eefcbe8caaa1f004f16ab76b204b5e1dbd58ff81b899f21cd40541232f AS builder
LABEL maintainer="ODL DevOps <mitx-devops@mit.edu>"

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
WORKDIR /tmp
COPY apt.txt /tmp/apt.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        $(grep -vE "^\s*#" apt.txt | tr "\n" " ") \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libxmlsec1-dev \
        libjpeg-dev \
        zlib1g-dev \
        pkg-config \
        libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /tmp/apt.txt

# Add, and run as, non-root user.
RUN mkdir /src \
    && adduser --disabled-password --gecos "" mitodl \
    && mkdir /var/media && chown -R mitodl:mitodl /var/media

# Install Python packages
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest@sha256:e590846f4776907b254ac0f44b5b380347af5d90d668138ca7938d1b0c2f98d3 /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock /src/
RUN mkdir -p /opt/venv && chown -R mitodl:mitodl /src /opt/venv

USER mitodl
WORKDIR /src
RUN uv sync --frozen --no-install-project --no-dev


FROM node:24-slim@sha256:24dc26ef1e3c3690f27ebc4136c9c186c3133b25563ae4d7f0692e4d1fe5db0e AS node_builder
COPY . /src
WORKDIR /src
ENV NODE_ENV=production
RUN yarn install --immutable \
    && node node_modules/webpack/bin/webpack.js --config webpack.config.prod.js --bail


# Runtime stage
FROM python:3.13-slim@sha256:dc1546eefcbe8caaa1f004f16ab76b204b5e1dbd58ff81b899f21cd40541232f AS runtime

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV="/opt/venv" \
    XDG_CACHE_HOME=/tmp/.cache
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install only runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libxml2 \
        libxslt1.1 \
        libpq5 \
        libxmlsec1 \
        libjpeg62-turbo \
        zlib1g \
        libmagic1 \
        net-tools \
        postgresql-client \
        libpoppler-cpp2 \
    && rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN adduser --disabled-password --gecos "" mitodl \
    && mkdir -p /src /var/media \
    && chown -R mitodl:mitodl /src /var/media

# Copy virtual environment from builder
COPY --from=builder --chown=mitodl:mitodl /opt/venv /opt/venv

# Copy uv binary from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx

# Add project
COPY --chown=mitodl:mitodl . /src
WORKDIR /src
RUN find /src -type f -name "*.py" -exec chmod 644 {} \; \
    && find /src -type f -name "*.sh" -exec chmod 755 {} \; \
    && find /src -type d -exec chmod 755 {} \;

USER mitodl

EXPOSE 8053
ENV PORT=8053

CMD ["uwsgi", "uwsgi.ini"]


FROM runtime AS production

COPY --from=node_builder --chown=mitodl:mitodl /src/static /src/static
COPY --from=node_builder --chown=mitodl:mitodl /src/webpack-stats.json /src/webpack-stats.json

from builder as dev

RUN uv sync --locked --dev
