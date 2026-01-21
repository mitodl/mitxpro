# Build stage
FROM python:3.13.7-slim as builder
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

# pip
RUN curl --silent --location https://bootstrap.pypa.io/get-pip.py | python3 -

# Add, and run as, non-root user.
RUN mkdir /src \
    && adduser --disabled-password --gecos "" --uid 1001 mitodl \
    && mkdir /var/media && chown -R mitodl:mitodl /var/media

# Install Python packages
## Set some poetry config
ENV POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/tmp/cache/poetry' \
    POETRY_HOME='/home/mitodl/.local' \
    VIRTUAL_ENV="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH"

COPY pyproject.toml poetry.toml poetry.lock /src/
RUN chown -R mitodl:mitodl /src \
    && mkdir ${VIRTUAL_ENV} && chown -R mitodl:mitodl ${VIRTUAL_ENV}

## Install poetry itself, and pre-create a venv with predictable name
USER mitodl
RUN curl -sSL https://install.python-poetry.org \
    | POETRY_VERSION=${POETRY_VERSION} POETRY_HOME=${POETRY_HOME} python3 -q
WORKDIR /src
RUN python3 -m venv $VIRTUAL_ENV \
    && poetry install --only=main

# Runtime stage
FROM python:3.13.7-slim as runtime

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
    && rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN adduser --disabled-password --gecos "" --uid 1001 mitodl \
    && mkdir -p /src /var/media \
    && chown -R mitodl:mitodl /src /var/media

# Copy virtual environment from builder
COPY --from=builder --chown=mitodl:mitodl /opt/venv /opt/venv

# Add project
COPY --chown=mitodl:mitodl . /src
WORKDIR /src
RUN find /src -type f -name "*.py" -exec chmod 644 {} \; \
    && find /src -type d -exec chmod 755 {} \;

USER mitodl

EXPOSE 8053
ENV PORT=8053

CMD ["uwsgi", "uwsgi.ini"]
