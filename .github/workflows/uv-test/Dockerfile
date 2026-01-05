FROM debian:bookworm

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

# Create piku user and directories
RUN useradd -m -s /bin/bash piku \
 && mkdir -p /home/piku/.piku/apps \
 && mkdir -p /home/piku/.piku/envs \
 && mkdir -p /home/piku/.piku/logs \
 && mkdir -p /home/piku/.piku/uwsgi \
 && chown -R piku:piku /home/piku

USER piku
WORKDIR /home/piku
ENV PATH="/home/piku/.local/bin:$PATH"

# Install uv for piku user and pre-install Python versions
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && /home/piku/.local/bin/uv python install 3.11 3.12

VOLUME ["/run"]

CMD ["/bin/bash", "/run/tests/uv/test_uv.sh"]
