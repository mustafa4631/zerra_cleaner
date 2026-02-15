# GK Healter

[Icon](/gk-healter/icons/hicolor/scalable/apps/io.github.gkdevelopers.GKHealter.svg)

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
- **Build System:** [Meson](https://mesonbuild.com/) / Make
- **Packaging:** [Flatpak](https://flatpak.org/), Debian (.deb), Arch (PKGBUILD), RPM (.spec)

## Installation

### Flatpak (any distro)

```bash
flatpak install flathub io.github.gkdevelopers.GKHealter
flatpak run io.github.gkdevelopers.GKHealter
```

### Arch Linux (AUR / PKGBUILD)

```bash
# Using the bundled PKGBUILD
cd packaging/arch
makepkg -si
```

### Debian / Ubuntu (.deb)

```bash
cd gk-healter
make deb
sudo dpkg -i gk-healter_0.1.0_all.deb
```

### Fedora / openSUSE (RPM)

```bash
# Build via rpmbuild using the bundled spec
rpmbuild -ba packaging/rpm/gk-healter.spec
```

### Generic install (any distro)

```bash
cd gk-healter
sudo make install
# To remove:
sudo make uninstall
```

## Build from Source (Meson)

```bash
git clone github.com/GK-Developers/GK-Healter.git
cd GK-Healter/gk-healter

meson setup _build
meson compile -C _build
sudo meson install -C _build
```

### Build Dependencies

| Dependency | Arch | Debian/Ubuntu | Fedora |
|---|---|---|---|
| Python 3 | `python` | `python3` | `python3` |
| PyGObject | `python-gobject` | `python3-gi` | `python3-gobject` |
| GTK 3 | `gtk3` | `gir1.2-gtk-3.0` | `gtk3` |
| Polkit | `polkit` | `policykit-1` | `polkit` |
| Meson | `meson` | `meson` | `meson` |

## Packaging

Packaging files for each distribution are included in the repository:

| Format | File | Location |
|---|---|---|
| Flatpak | `flathub_submission.yml` | `gk-healter/` |
| Arch Linux | `PKGBUILD` | `gk-healter/packaging/arch/` |
| RPM (Fedora/openSUSE) | `gk-healter.spec` | `gk-healter/packaging/rpm/` |
| Debian/Ubuntu | `debian/control` | `gk-healter/debian/` |

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
