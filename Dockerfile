FROM ubuntu:24.04
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list || true && \
    sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources || true && \
	apt-get update && \
	apt install -y \
	wget tar python3 python3-flask python3-gevent python3-cachetools python3-flask-cors python3-distutils-extra libkpathsea6 && \
	wget --output-document /tmp/texlive.tar.gz "http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz" && \
	cd /tmp && tar xf texlive.tar.gz && cd install* && echo "I" | ./install-tl && cd / && rm -r /tmp/texlive.tar.gz /tmp/install* && \
    echo 'export PATH=/usr/local/texlive/2025/bin/x86_64-linux:$PATH\nexport MANPATH=/usr/local/texlive/2025/texmf-dist/doc/man:$MANPATH\nexport INFOPATH=/usr/local/texlive/2025/texmf-dist/doc/info:$INFOPATH' >> /etc/profile && \
	mkdir -p /etc/texmf && ln -s /usr/local/texlive/2025/ /etc/texmf/web2c && \
	ln -s /usr/local/texlive/2025 /usr/share/texlive
COPY . /app
WORKDIR /app
