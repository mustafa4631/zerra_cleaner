# Docker-based Testing Environment for GK-Healter

This directory contains a minimal container setup to exercise the application in a controlled environment.

## Structure

- `Dockerfile` – base image with Python, GTK, and dependencies; copies the repository into `/workspace`.
- `scenarios/` – helper scripts that deliberately corrupt the filesystem at varying severity levels (low, medium, critical).

## Usage

Build the image from the project root:

```sh
cd /home/egehan/development/GK-Healter
docker build -t gk-healter-test -f tests/docker/Dockerfile .
```

Run the container interactively, mount any additional volumes if needed:

```sh
docker run --rm -it --privileged \
    -v /dev:/dev \ # if hardware interaction ever required
    -v $(pwd):/workspace \
    gk-healter-test
```

Inside the container you can execute any scenario script:

```sh
bash tests/docker/scenarios/low_bloat.sh
python3 -m pytest tests   # run unit tests against the broken state
```

Each scenario script prints a confirmation message when the junk has been created. After running GK‑Healter, re‑run the one‑liner validations listed in the project README or test files to ensure the cleaners worked.

> **Note:** All commands are safe to execute inside throw‑away containers only. They modify only container filesystem and are intended for automation and CI.