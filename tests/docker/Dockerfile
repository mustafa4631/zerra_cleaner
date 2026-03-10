# Base image for running GK-Healter inside CI or local development
# This container is intended to be discarded after tests complete.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# install python and minimal tooling
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-pip python3-gi gir1.2-gtk-3.0 \
       git procps jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# create workspace and copy source code
WORKDIR /workspace
COPY . /workspace

# install python requirements; tests expect pytest etc.
RUN pip3 install --no-cache-dir -r requirements.txt \
    && pip3 install --no-cache-dir pytest pytest-cov

# default command lists available scenarios
CMD ["bash","-c","echo 'Container ready; mount project and run \"bash tests/docker/create_scenarios.sh\" to populate test mess' && bash"]
