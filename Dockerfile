FROM ubuntu:24.04
# prepare font yourself
# COPY ./myfont /usr/local/share/fonts
COPY . /app
# RUN rm -rf /app/myfont /app/.git && \
# 	sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list || true && \
# 	sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources || true && \
# 	apt-get update && \
# 	# generate font package
# 	apt list 'fonts-*' | grep 'fonts-' | grep -v fonts-ubuntu-classic | cut -d/ -f1 | tr '\n' ' ' > /tmp/font_packages.txt && \
# 	# install packages and fonts
# 	DEBIAN_FRONTEND=noninteractive echo 'yes' | apt install -y ttf-* wget tar python3 python3-flask python3-gevent python3-cachetools python3-flask-cors python3-distutils-extra libkpathsea6 $(cat /tmp/font_packages.txt) ttf* && rm /tmp/font_packages.txt && \
# 	# get texlive installer
# 	wget --output-document /tmp/texlive.tar.gz "http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz" && \
# 	# install texlive
# 	cd /tmp && tar xf texlive.tar.gz && cd install* && echo "I" | ./install-tl -repository "https://mirrors.ustc.edu.cn/CTAN/systems/texlive/tlnet/" && cd / && rm -r /tmp/texlive.tar.gz /tmp/install* && \
# 	# create texlive symlink
# 	mkdir -p /etc/texmf && ln -s /usr/local/texlive/2025/ /etc/texmf/web2c && ln -s /usr/local/texlive/2025 /usr/share/texlive && \
# 	# update font cache
# 	cp /usr/local/texlive/2025/texmf-var/fonts/conf/texlive-fontconfig.conf /etc/fonts/conf.d/09-texlive.conf && fc-cache -fsv
WORKDIR /app
ENV PATH=/usr/local/texlive/2025/bin/x86_64-linux:$PATH
