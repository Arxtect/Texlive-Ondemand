# =====================================
# Stage 1: Base system and TeXLive installation
# =====================================
FROM ubuntu:24.04 AS texlive-base

# Configure package sources
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list || true && \
    sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources || true

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt install -y \
        wget tar python3 python3-flask python3-gevent \
        python3-cachetools python3-flask-cors python3-distutils-extra \
        libkpathsea6 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install TeXLive
RUN wget --output-document /tmp/texlive.tar.gz \
        "http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz" && \
    cd /tmp && tar xf texlive.tar.gz && cd install* && \
    echo "I" | ./install-tl -repository \
        "https://mirrors.ustc.edu.cn/CTAN/systems/texlive/tlnet/" && \
    cd / && rm -r /tmp/texlive.tar.gz /tmp/install* && \
    mkdir -p /etc/texmf && \
    ln -s /usr/local/texlive/2025/ /etc/texmf/web2c && \
    ln -s /usr/local/texlive/2025 /usr/share/texlive

# =====================================
# Stage 2: System fonts installation
# =====================================
FROM texlive-base AS system-fonts

# Install system font packages
RUN apt-get update && \
    apt list 'fonts-*' | grep 'fonts-' | grep -v fonts-ubuntu-classic | \
        cut -d/ -f1 | tr '\n' ' ' > /tmp/font_packages.txt && \
    DEBIAN_FRONTEND=noninteractive echo 'yes' | apt install -y \
        ttf-* $(cat /tmp/font_packages.txt) ttf* && \
    rm /tmp/font_packages.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# =====================================
# Stage 3: Application layer
# =====================================
FROM system-fonts

# Copy custom fonts first
COPY ./myfont /usr/local/share/fonts

# Copy application code last
COPY . /app

# Cleanup and configure fonts
RUN rm -rf /app/myfont /app/.git && \
    cp /usr/local/texlive/2025/texmf-var/fonts/conf/texlive-fontconfig.conf \
        /etc/fonts/conf.d/09-texlive.conf && \
    fc-cache -fsv

WORKDIR /app
ENV PATH=/usr/local/texlive/2025/bin/x86_64-linux:$PATH
