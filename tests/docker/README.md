# Docker-based Testing Environment for GK-Healter

This directory contains a minimal container setup to exercise the application in a controlled environment.

## Structure

- `Dockerfile` – base image with Python, GTK, and dependencies; copies the repository into `/workspace`.
- `scenarios/` – helper scripts that deliberately corrupt the filesystem at varying severity levels (low, medium, critical).

## Usage

Build the image from the project root (using Pardus 25 base). Run this **before** launching a container, otherwise `docker run` will try to pull `gk-healter-test` from a registry and fail. You can override the base with the `etap` variant if needed:

```sh
cd /home/egehan/development/GK-Healter
# default uses pardus/yirmibes
sudo docker build -t gk-healter-test -f tests/docker/Dockerfile .

# or build against the etap flavor
docker build --build-arg BASE_IMAGE=pardus/etap:latest \
       -t gk-healter-test:etap \
       -f tests/docker/Dockerfile .
```
(omit `sudo` once your user is in the `docker` group and you have re‑logged.)

Run the container interactively, mount any additional volumes if needed.  

> ⚠️ You must be root or belong to the `docker` group (log out / back in after adding yourself) to talk to the daemon. Add your user with `sudo usermod -aG docker $USER` if necessary.

```sh
# as root
sudo docker run --rm -it --privileged \
    -v /dev:/dev \
    -v $(pwd):/workspace \
    gk-healter-test

# or as a docker‑group member
docker run --rm -it --privileged \
    -v /dev:/dev \
    -v $(pwd):/workspace \
    gk-healter-test

> **fish users:** replace `$(pwd)` with `(pwd)` when running commands interactively. keep comments on separate lines as shown above; fish treats `#` differently.
```

Inside the container you can execute any scenario script:

```sh
bash tests/docker/scenarios/low_bloat.sh
python3 -m pytest tests   # run unit tests against the broken state
```

Each scenario script prints a confirmation message when the junk has been created. After running GK‑Healter, re‑run the one‑liner validations listed in the project README or test files to ensure the cleaners worked.

> **Note:** All commands are safe to execute inside throw‑away containers only. They modify only container filesystem and are intended for automation and CI.