# GK Healter

GK Healter is a professional, lightweight system maintenance utility designed for Linux desktops. It emphasizes safety and efficiency, providing users with a reliable way to recover disk space by identifying and removing redundant files without compromising system stability.

Developed by **Egehan KAHRAMAN** and **Mustafa GÖKPINAR** — **GK Developers**.

## Key Features

- **Package Management:** Clean APT environment, including downloaded package archives and partial files.
- **System Maintenance:** Remove redundant system logs and vacuum the system journal.
- **Application Hygiene:** Clear application-specific data such as browser caches and thumbnail galleries.
- **Automated Operations:** Intelligent maintenance engine that can be scheduled based on system idle time or disk usage thresholds.
- **Detailed Tracking:** Comprehensive history of all cleaning operations and the total space recovered.
- **Native Experience:** Built with a modern GTK interface that respects system themes and dark mode settings.

## Screenshot

![GK Healter Main Window](screenshots/main-window.png)

## Technology Stack


- **Language:** [Python 3](https://www.python.org/)
- **GUI Toolkit:** [GTK 3 (PyGObject)](https://pygobject.readthedocs.io/)
- **Build System:** [Meson](https://mesonbuild.com/)
- **Packaging:** [Flatpak](https://flatpak.org/)

## Installation from Flathub

Once the application is published on Flathub, you can install it using:

```bash
flatpak install flathub io.github.gkdevelopers.GKHealter
```

To run the application:

```bash
flatpak run io.github.gkdevelopers.GKHealter
```

## Build from Source

To build and install the application directly onto your system using Meson:

```bash
# Clone the repository
git clone github.com/GK-Developers/GK-Healter.git
cd gk-healter

# Setup the build directory
meson setup _build

# Compile and install
sudo meson install -C _build
```

## Packaging

The official Flatpak package is maintained in a separate repository to follow Flathub standards.

- **Source Repository:** `gkdevelopers/gk-healter` (This repository)
- **Packaging Repository:** `gkdevelopers/flathub` (Contains the Flatpak manifest)
- **Manifest File:** `flathub_submission.yml` (Template for the packaging repo)

To build locally, you can use the provided `flathub_submission.yml` but ensure you commit your changes to the source repo first, as it pulls from Git.

## Contributing Guidelines

Contributions are welcome to help improve GK Healter. You can contribute by reporting bugs, suggesting new cleaning modules, or submitting pull requests for code improvements and translations.

## Support

If you find this project useful, you can support its development through GitHub issues by providing feedback. Optional financial support is appreciated but never required for continued use of the software.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## Project Links

- **Homepage:** [github.com/GK-Developers/GK-Healter](github.com/GK-Developers/GK-Healter)
- **Bug Tracker:** [github.com/GK-Developers/GK-Healter/issues](github.com/GK-Developers/GK-Healter/issues)
- **Source Code:** [github.com/GK-Developers/GK-Healter](github.com/GK-Developers/GK-Healter)
