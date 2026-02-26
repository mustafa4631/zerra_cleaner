# GK Healter

<div align="center">
  <a href="README.tr.md">🇹🇷 Türkçe (Turkish)</a> &nbsp;|&nbsp; 
  <a href="README.md">🇬🇧 English</a>
</div>

<center>

![Icon](/gk-healter/icons/hicolor/256x256/apps/io.github.gkdevelopers.GKHealter.png)
</center>

**GK Healter** is a professional system maintenance and health-monitoring utility designed primarily for **Pardus** and Debian-based Linux distributions. It emphasizes safety and efficiency, providing users with reliable disk space recovery, error detection, and proactive maintenance capabilities without compromising system stability.

> 🏆 Developed for **TEKNOFEST 2026 — Pardus Bug Catching and Suggestion Competition** (Development Category).

Developed by **Egehan KAHRAMAN** and **Mustafa GÖKPINAR** — **GK Developers**.

## Key Features

### Pardus-Specific Diagnostics
- **Pardus Repository Health Check:** Validates APT sources, detects broken/held packages, checks Pardus-specific services (`pardus-*`, `eta-*`).
- **Pardus Version Detection:** Identifies Pardus release info and provides distribution-aware recommendations.
- **Broken Package Detection:** Uses `dpkg --audit` and `apt-get check` for Debian/Pardus-native package integrity.

### System Maintenance
- **Package Management:** Clean APT cache, autoremove orphan packages, fix broken dependencies via polkit-authenticated actions.
- **System Log Cleanup:** Remove redundant logs, vacuum systemd journal, clean old coredumps.
- **Application Hygiene:** Clear browser caches, thumbnail galleries, and user-specific temporary files.
- **Safety-First Approach:** Whitelist-based deletion prevents accidental removal of critical system files.

### Monitoring & Intelligence
- **Real-Time Health Score:** CPU, RAM, and disk usage monitoring with a composite health score (0–100).
- **Hybrid AI Analysis:** Offline rule-based `LocalAnalysisEngine` always available; optional cloud enrichment via Gemini/OpenAI APIs.
- **Smart Recommendations:** Rule-based engine generates actionable suggestions based on system metrics.
- **Service Analyzer:** Detects failed systemd services and slow-starting units.
- **Log Analyzer:** Identifies critical/error-level journal entries with severity classification.

### Security Audit
- **World-Writable File Detection:** Scans system directories for insecure permissions.
- **SUID/SGID Binary Audit:** Identifies unexpected set-uid binaries against a known whitelist.
- **Sudoers Risk Analysis:** Flags dangerous `NOPASSWD: ALL` entries.
- **SSH Hardening Check:** Validates `sshd_config` against security best practices.
- **Unattended-Upgrades Monitoring:** Verifies automatic security updates are enabled.
- **Failed Login Tracking:** Summarizes authentication failures from journal.

### Automation
- **Intelligent Auto-Maintenance:** Scheduled cleaning based on idle time, disk thresholds, and power status.
- **Cleaning History:** Comprehensive tracking of all operations with timestamps and space recovered.

### User Experience
- **Native GTK 3 Interface:** Modern, responsive design that respects system themes and dark mode.
- **Multi-Language Support:** Turkish and English with extensible JSON-based i18n system.
- **Report Export:** Generate TXT, HTML, and JSON system analysis reports for documentation and demo purposes.
- **Dedicated Security Page:** Separate tab with Pardus verification data, colour-coded findings, and one-click export.

## Screenshot
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-49-28" src="https://github.com/user-attachments/assets/c45eaf08-6e30-40e5-af78-c2c56e74bbab" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-48-28" src="https://github.com/user-attachments/assets/da6e4b54-7c6b-4412-91e9-29c17e084356" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-48-20" src="https://github.com/user-attachments/assets/20d80451-c0d5-4697-85fe-d8f3db95e3e6" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-48-11" src="https://github.com/user-attachments/assets/0dd369d8-fa3e-4ba2-af60-a1faf10ee1c5" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-48-03" src="https://github.com/user-attachments/assets/3a558a80-29f1-4215-bf9e-eea60a25fa07" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-47-46" src="https://github.com/user-attachments/assets/a6037c33-21ac-44d9-b01f-c1b7b3ddd744" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-47-07" src="https://github.com/user-attachments/assets/2f51be6e-1ce6-40c4-b27c-dd31a561409b" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-46-24" src="https://github.com/user-attachments/assets/41176ef1-8d15-4f48-a020-1db4a5446275" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-46-10" src="https://github.com/user-attachments/assets/dffe74c2-ff14-41af-9964-e6ee06a9fef8" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-45-19" src="https://github.com/user-attachments/assets/700bd689-1f7d-4a39-bbc9-5b757f2b5279" />
<img width="1920" height="1080" alt="Ekran görüntüsü_2026-02-26_23-45-10" src="https://github.com/user-attachments/assets/02ff7df4-b06c-41a2-83bc-49430ab28654" />



## Technology Stack

- **Language:** [Python 3](https://www.python.org/)
- **GUI Toolkit:** [GTK 3 (PyGObject)](https://pygobject.readthedocs.io/)
- **Build System:** [Meson](https://mesonbuild.com/) / Make
- **Testing:** [pytest](https://docs.pytest.org/) (298 tests, %75+ coverage) with CI via GitHub Actions
- **Packaging:** [Flatpak](https://flatpak.org/), Debian (.deb), Arch (PKGBUILD), RPM (.spec)
- **Privilege Escalation:** Polkit (pkexec) with custom policy file

## Architecture

```
src/
├── main.py                  # Application entry point
├── ui.py                    # GTK UI controller (Builder pattern)
├── cleaner.py               # Safety-first cleaning engine
├── health_engine.py         # Real-time system health monitoring
├── pardus_analyzer.py       # Pardus/Debian-specific diagnostics
├── security_scanner.py      # System security audit engine
├── pardus_verifier.py       # Pardus identity verification & evidence
├── report_exporter.py       # TXT / HTML / JSON report generator
├── distro_manager.py        # Multi-distro package manager abstraction
├── disk_analyzer.py         # Large file discovery
├── log_analyzer.py          # Journal error analysis
├── service_analyzer.py      # Systemd service health
├── recommendation_engine.py # Rule-based system recommendations
├── ai_engine.py             # Hybrid AI: local analysis + cloud enrichment
├── auto_maintenance_manager.py # Scheduled maintenance logic
├── settings_manager.py      # Persistent configuration
├── history_manager.py       # Cleaning history tracking
├── i18n_manager.py          # Internationalization (JSON-based)
├── logger.py                # Centralized logging (rotating files)
└── utils.py                 # Shared utility functions
```

## Installation

### Pardus / Debian / Ubuntu (.deb) — Recommended

```bash
cd gk-healter
make deb
sudo dpkg -i gk-healter_0.1.6_all.deb
sudo apt-get install -f  # Fix any missing dependencies
```

### Flatpak (any distro)

```bash
flatpak install flathub io.github.gkdevelopers.GKHealter
flatpak run io.github.gkdevelopers.GKHealter
```

### Arch Linux (AUR / PKGBUILD)

```bash
cd packaging/arch
makepkg -si
```

### Fedora / openSUSE (RPM)

```bash
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
git clone https://github.com/GK-Developers/GK-Healter.git
cd GK-Healter/gk-healter

meson setup _build
meson compile -C _build
sudo meson install -C _build
```

### Build Dependencies

| Dependency | Pardus/Debian | Arch | Fedora |
|---|---|---|---|
| Python 3 | `python3` | `python` | `python3` |
| PyGObject | `python3-gi` | `python-gobject` | `python3-gobject` |
| GTK 3 | `gir1.2-gtk-3.0` | `gtk3` | `gtk3` |
| psutil | `python3-psutil` | `python-psutil` | `python3-psutil` |
| Polkit | `policykit-1` | `polkit` | `polkit` |
| Meson | `meson` | `meson` | `meson` |

## Running Tests

```bash
pip install pytest pytest-cov
pytest -v --cov=src --cov-report=term-missing
```

**298 tests** covering 17 modules across 18 test files.

## Packaging

| Format | File | Location |
|---|---|---|
| Flatpak | `flathub_submission.yml` | `gk-healter/` |
| Arch Linux | `PKGBUILD` | `gk-healter/packaging/arch/` |
| RPM | `gk-healter.spec` | `gk-healter/packaging/rpm/` |
| Debian/Pardus | `debian/control` | `gk-healter/debian/` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## Project Links

- **Homepage:** [https://github.com/GK-Developers/GK-Healter](https://github.com/GK-Developers/GK-Healter)
- **Bug Tracker:** [https://github.com/GK-Developers/GK-Healter/issues](https://github.com/GK-Developers/GK-Healter/issues)
- **Source Code:** [https://github.com/GK-Developers/GK-Healter](https://github.com/GK-Developers/GK-Healter)
