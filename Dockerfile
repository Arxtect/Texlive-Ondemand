# =====================================
# Stage 1: Base system and TeXLive installation
# =====================================
FROM ubuntu:24.04

# then Copy application code
COPY . /app

RUN mv /app/myfont /usr/local/share/fonts && rm -rf /app/.git && \
    sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list || true && \
    sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources || true && \
    apt-get update && apt list 'fonts-*' | grep 'fonts-' | grep -v fonts-ubuntu-classic | cut -d/ -f1 | tr '\n' ' ' > /tmp/font_packages.txt && \
    DEBIAN_FRONTEND=noninteractive echo 'yes' | apt install -y \
        ttf-* $(cat /tmp/font_packages.txt) ttf* wget tar python3 python3-flask python3-gevent \
        python3-cachetools python3-flask-cors python3-distutils-extra xz-utils \
        libkpathsea6 rsync && \
    rm /tmp/font_packages.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/lib/texlive/repo/archive && mkdir -p /var/lib/texlive/repo/tlpkg && \
    rsync -av --delete --progress rsync://mirrors.ustc.edu.cn/CTAN/systems/texlive/tlnet/ /var/lib/texlive/repo && \
    cd /tmp && tar xf /var/lib/texlive/repo/install-tl-unx.tar.gz && cd install* && \
    echo "I" | ./install-tl -repository /var/lib/texlive/repo && \
    cd / && rm -r /tmp/install* && mkdir -p /etc/texmf && \
    ln -s /usr/local/texlive/2025/ /etc/texmf/web2c && \
    ln -s /usr/local/texlive/2025 /usr/share/texlive && \
    cp /usr/local/texlive/2025/texmf-var/fonts/conf/texlive-fontconfig.conf /etc/fonts/conf.d/09-texlive.conf && \
    mkdir -p /var/lib/texlive/repo/simple && mv /usr/local/share/fonts/process_tlpdb.py /var/lib/texlive/repo/simple/ && \
    cd /var/lib/texlive/repo/simple && python3 process_tlpdb.py -d ../tlpkg/texlive.tlpdb texlive.simple.tlpdb ../archive && \
    cat /var/lib/texlive/repo/simple/texlive.simple.tlpdb | xz > /app/tlpkg.txt && \
    cat /usr/local/texlive/2025/texmf-var/fonts/map/pdftex/updmap/pdftex.map | xz > /app/pdftex.map && \
    cat /tmp/vf.txt | xz > /app/vfpkg.txt && \
    rm -rf /var/lib/texlive/repo/archive /var/lib/texlive/repo/tlpkg /var/lib/texlive/repo/install* /var/lib/texlive/repo/update* /var/lib/texlive/repo/README.md /var/lib/texlive/repo/TEXLIVE_* && \
    fc-cache -fsv

WORKDIR /app
ENV PATH=/usr/local/texlive/2025/bin/x86_64-linux:$PATH
