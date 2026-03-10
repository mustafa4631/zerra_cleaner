# Base image for running GK-Healter inside CI or local development.
# Using the official Pardus 25 (yirmibes) image as requested.
# This container is intended to be discarded after tests complete.

# allow switching between the main Pardus 25 base and the etap variant
ARG BASE_IMAGE=pardus/yirmibes:latest
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

# install python and minimal tooling
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-pip python3-gi gir1.2-gtk-3.0 \
       # install venv early so later builds don't need it
       python3.13-venv \
       git procps jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# create workspace and copy source code
WORKDIR /workspace
COPY . /workspace

# allow skipping apt-get update when rebuilding frequently
ARG SKIP_APT_UPDATE=false
# optionally skip apt update/install when rebuilding frequently
RUN if [ "$SKIP_APT_UPDATE" = "false" ]; then \
        apt-get update && \
        apt-get install -y --no-install-recommends python3.13-venv; \
    else \
        echo "skipping apt update and venv install"; \
    fi && \
    python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest pytest-cov && \
    rm -rf /var/lib/apt/lists/*

# make the virtualenv the default python environment
ENV PATH="/opt/venv/bin:$PATH"

# default command lists available scenarios
CMD ["bash","-c","echo 'Container ready; mount project and run \"bash tests/docker/create_scenarios.sh\" to populate test mess' && bash"]
