FROM ubuntu:24.04

ARG LIBMGBA_TAG=0.2.0-2
ARG LIBMGBA_VER=0.2.0

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# Dependencias nativas necessarias para audio/GUI e runtime do libmgba-py em Linux (glibc).
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    unzip \
    python3-tk \
    portaudio19-dev \
    libmgba0.10t64 \
    libglib2.0-0 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    libxxf86vm1 \
    libgl1 \
    libegl1 \
    libepoxy0 \
    libasound2t64 \
    libpulse0 \
    libdbus-1-3 \
    libnotify4 \
    libsqlite3-0 \
    zlib1g \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Forca uso do binding Linux do libmgba-py.
RUN rm -rf /app/mgba && \
    curl -fsSL -o /tmp/libmgba.zip \
    "https://github.com/hanzi/libmgba-py/releases/download/${LIBMGBA_TAG}/libmgba-py_${LIBMGBA_VER}_ubuntu-lunar.zip" && \
    unzip -q /tmp/libmgba.zip -d /app && \
    rm -f /tmp/libmgba.zip

# Marca requisitos como resolvidos para evitar prompt interativo na inicializacao.
RUN python -c "from modules.runtime import get_base_path; \
from requirements import get_requirements_hash; \
path = get_base_path() / '.last-requirements-check'; \
path.write_text(get_requirements_hash())"

RUN mkdir -p /app/roms /app/profiles /app/saves /app/screenshots /app/stats /app/logs /app/config

# Evita prompt interativo do updater em ambiente de container.
RUN mkdir -p /app/.git

EXPOSE 8888

CMD ["python", "pokebot.py", "-hl", "-nv", "-na", "Sapphire"]
