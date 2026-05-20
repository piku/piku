FROM ubuntu:plucky
RUN apt-get update && apt-get install -y \
    nginx \
    python3-pip \
    python3-click \
    python3-virtualenv \
    uwsgi \
    uwsgi-plugin-python3 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
CMD ["/usr/bin/python3", "/run/piku.py"]
