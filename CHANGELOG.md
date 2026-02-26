# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] — 2026-02-26

### Fixed
- **Settings page layout** — AI Configuration section (Provider, API Key, Model) was nested
  inside the Auto Maintenance detail box, making it invisible when auto-maintenance was disabled.
  Moved to a top-level settings section so it is always accessible.
- **About dialog license** — incorrectly displayed GPL-3.0; corrected to MIT to match the
  actual project license (`LICENSE` file and AppStream metainfo).
- **RPM spec version** — synced from `0.1.4` → `0.1.6`.
- **AppStream metainfo release date** — updated to actual release date (2026-02-26).

### Changed
- Version bumped to `0.1.6` across all packaging and metadata files
  (`__init__.py`, `meson.build`, `Makefile`, `PKGBUILD`, `debian/changelog`,
  `metainfo.xml`, About dialog, `README.md`, `README.tr.md`).

## [0.1.5] — 2026-02-21

### Added
- **Pardus Verification Module** (`pardus_verifier.py`) — collects /etc/os-release, lsb_release,
  hardware info, installed Pardus packages, desktop environment, and hostname into a structured
  report for competition evidence / jury demo.
- **Report Exporter Module** (`report_exporter.py`) — generates comprehensive system analysis
  reports in TXT, HTML (inline CSS, self-contained), and JSON formats.
- **Security Page** — dedicated GTK stack page (`page_security`) with:
  - Pardus verification section showing live system identity data
  - Colour-coded security findings (critical/high/warning)
  - One-click security scan button
  - Report export button (TXT + HTML)
- **Turkish README** (`README.tr.md`) — full Turkish documentation with project overview,
  Pardus-specific features, architecture, installation, security approach.
- 18 new i18n keys for Security page, Pardus verification, and report export
  (both `en.json` and `tr.json`).
- 52 new test functions across 2 new test files (`test_pardus_verifier.py`,
  `test_report_exporter.py`) — total test count: 298.

### Fixed
- **Flatpak manifest** (`flathub_submission.yml`) — added missing `https://` protocol to git URL.
- `meson.build` — added `pardus_verifier.py`, `report_exporter.py`, `security_scanner.py`,
  and `distro_manager.py` to the `python_sources` install list.

### Changed
- Security audit findings moved from Insights sub-section to dedicated Security page.
- `ui.py` refactored with new signal handlers, widget bindings, and background threads
  for security scan, Pardus verification display, and report export.

## [0.1.3] — 2026-02-19

### Added
- **Pardus mirror health check** — tests reachability and latency of `depo.pardus.org.tr` mirrors.
- **Pardus release compatibility** — validates APT source codenames against running OS version.
- **APT/dpkg log analysis** — summarizes package install/remove/upgrade activity over the last 7 days.
- API key file-permission hardening (`chmod 600` on `settings.json`, `700` on config dir).
- `__version__` constant in `src/__init__.py` for programmatic version access.
- `CHANGELOG.md` (this file).
- 23 new i18n keys for mirror health, release compatibility, log analysis, health status labels,
  and recommendation engine messages (both `en.json` and `tr.json`).
- CI step for AppStream metainfo and desktop file validation.

### Fixed
- **Cleaner `is_safe_to_delete` bug** — marker paths (`/usr/bin/apt` for autoremove) were
  incorrectly blocked by the `/usr/bin` forbidden prefix. Marker paths are now explicitly
  allowed through the safety check.
- Missing 9 Turkish translation keys (`health_cores`, `health_free`, `pardus_detected`,
  `pardus_features_active`, `pardus_insights_subtitle`, `pardus_chip_*`, `pardus_svc_not_installed`).
- RPM spec version synced from `0.1.0` → `0.1.3`.
- RPM spec missing `python3-psutil` runtime dependency added.
- Metainfo.xml URLs now include `https://` protocol prefix.
- Hardcoded English strings in `health_engine.py` and `recommendation_engine.py` replaced
  with i18n function calls.

### Changed
- CI coverage threshold raised from 70 % to 75 %.

## [0.1.2] — 2026-02-15

### Added
- Security scanner module (`security_scanner.py`) with 6 audit types:
  world-writable files, SUID/SGID binaries, sudoers risk, SSH config,
  unattended upgrades, failed logins.
- Repository trust score calculation.
- Repair simulation (dry-run) for broken packages.
- 22 tests for `security_scanner.py`.

## [0.1.1] — 2026-02-10

### Added
- Full test suite: 170 tests across 16 modules.
- GitHub Actions CI pipeline (lint, multi-version test, deb packaging, release).
- Codecov integration with 70 % coverage minimum.
- Centralized logging with rotating file handler.
- `PardusAnalyzer` module with distribution detection, repo health, broken
  package detection, service analysis, update advisory, and dependency graph.

### Changed
- Replaced `print()` debugging with `logging` module throughout.
- License in metainfo.xml corrected from GPL-3.0 to MIT.

## [0.1.0] — 2026-01-28

### Added
- Initial release.
- GTK 3 desktop application with 6-page UI (Dashboard, Cleaner, Health,
  Insights, History, Settings).
- System cleaner with safety whitelist.
- Real-time health engine (CPU, RAM, Disk).
- Hybrid AI analysis engine (local rule-based + Gemini/OpenAI cloud).
- Multi-distro support (apt, pacman, dnf, zypper).
- Auto-maintenance manager.
- Turkish and English i18n.
- Debian, Arch, RPM, and Flatpak packaging.
- Polkit policy for privileged operations.
