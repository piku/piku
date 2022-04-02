FROM ubuntu:focal

ENV DEBIAN_FRONTEND=noninteractive

# Install the minimum amount of packages required for testing, which currently means:
# - minimal set of packages required to run Python 3
# - shipping versions of uWSGI and nginx (so that config files are put in the right places)
# Also, make sure we have a sane default locale inside the container

RUN apt-get update \
 && apt-get dist-upgrade -y \
 && apt-get install -y --no-install-recommends \
    apt-utils \
	ca-certificates \
	locales \
	curl \
	tzdata \
    git \
    build-essential \ 
    git \
    nginx \
    python3-pip \
    python3-click \
    python3-virtualenv \
    uwsgi \
    uwsgi-plugin-asyncio-python3 \
    uwsgi-plugin-python3 \
&& locale-gen en_US.UTF-8

ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

VOLUME ["/run"]

CMD ["/usr/bin/python3", "/run/piku.py"]
