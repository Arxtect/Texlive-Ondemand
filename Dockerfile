FROM ubuntu:24.04
RUN  sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list || true && \
     sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources || true && \
	 apt-get update && \
	 DEBIAN_FRONTEND=noninteractive apt install -q -y wget texlive-full python3 python3-flask python3-gevent python3-cachetools python3-flask-cors python3-distutils-extra libkpathsea-dev texlive-bibtex-extra texlive-fonts-extra texlive-humanities ttf-mscorefonts-installer
COPY . /app
WORKDIR /app
