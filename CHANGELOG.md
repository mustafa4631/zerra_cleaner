# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
