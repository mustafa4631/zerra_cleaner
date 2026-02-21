"""
GK Healter – Test Suite: pardus_verifier.py
Covers verify(), caching, sub-collectors, and text export.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from gk_healter_tests.helpers import src_import

mod = src_import("pardus_verifier")
PardusVerifier = mod.PardusVerifier


class TestVerify:
    """Full verify() orchestration tests."""

    @pytest.fixture
    def verifier(self):
        return PardusVerifier()

    def test_verify_pardus_detected(self):
        verifier = PardusVerifier()
        with patch.object(PardusVerifier, "_read_os_release", return_value={
                 "ID": "pardus", "PRETTY_NAME": "Pardus 23.2",
             }), \
             patch.object(PardusVerifier, "_read_lsb_release", return_value={
                 "distributor_id": "Pardus", "release": "23.2",
             }), \
             patch.object(PardusVerifier, "_collect_hardware_info", return_value={
                 "kernel": "6.1.0", "architecture": "x86_64",
                 "cpu_count": 4, "total_ram_bytes": 8589934592,
             }), \
             patch.object(PardusVerifier, "_check_pardus_packages", return_value=[
                 {"name": "pardus-software", "status": "installed"}
             ]), \
             patch.object(PardusVerifier, "_list_pardus_packages", return_value=["pardus-software"]), \
             patch.object(PardusVerifier, "_detect_desktop_environment", return_value="XFCE"):
            report = verifier.verify()
        assert report["is_pardus"] is True
        assert report["os_release"]["ID"] == "pardus"
        assert "timestamp" in report
        assert "hostname" in report
        assert report["desktop_environment"] == "XFCE"

    def test_verify_non_pardus(self):
        verifier = PardusVerifier()
        with patch.object(PardusVerifier, "_read_os_release", return_value={
                 "ID": "ubuntu", "PRETTY_NAME": "Ubuntu 24.04 LTS",
             }), \
             patch.object(PardusVerifier, "_read_lsb_release", return_value={
                 "distributor_id": "Ubuntu", "release": "24.04",
             }), \
             patch.object(PardusVerifier, "_collect_hardware_info", return_value={
                 "kernel": "6.5.0", "architecture": "x86_64",
                 "cpu_count": 8, "total_ram_bytes": 17179869184,
             }), \
             patch.object(PardusVerifier, "_check_pardus_packages", return_value=[]), \
             patch.object(PardusVerifier, "_list_pardus_packages", return_value=[]), \
             patch.object(PardusVerifier, "_detect_desktop_environment", return_value="GNOME"):
            report = verifier.verify()
        assert report["is_pardus"] is False

    def test_verify_caches_report(self, verifier):
        assert verifier.get_cached_report() is None
        with patch.object(PardusVerifier, "_read_os_release", return_value={"ID": "linux"}), \
             patch.object(PardusVerifier, "_read_lsb_release", return_value={}), \
             patch.object(PardusVerifier, "_collect_hardware_info", return_value={}), \
             patch.object(PardusVerifier, "_check_pardus_packages", return_value=[]), \
             patch.object(PardusVerifier, "_list_pardus_packages", return_value=[]), \
             patch.object(PardusVerifier, "_detect_desktop_environment", return_value=""):
            report = verifier.verify()
        assert verifier.get_cached_report() is report


class TestReadOsRelease:
    """Tests for _read_os_release."""

    def test_parses_os_release_file(self):
        content = (
            'ID=pardus\n'
            'PRETTY_NAME="Pardus 23.2"\n'
            'VERSION_ID="23.2"\n'
            '# comment line\n'
        )
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            result = PardusVerifier._read_os_release()
        assert result["ID"] == "pardus"
        assert result["PRETTY_NAME"] == "Pardus 23.2"
        assert result["VERSION_ID"] == "23.2"

    def test_missing_file_returns_empty(self):
        with patch("os.path.isfile", return_value=False):
            result = PardusVerifier._read_os_release()
        assert result == {}

    def test_handles_read_error(self):
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", side_effect=PermissionError("denied")):
            result = PardusVerifier._read_os_release()
        assert result == {}


class TestReadLsbRelease:
    """Tests for _read_lsb_release."""

    def test_parses_lsb_output(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = (
            "Distributor ID:\tPardus\n"
            "Description:\tPardus 23.2\n"
            "Release:\t23.2\n"
            "Codename:\tyirmiuc\n"
        )
        with patch("shutil.which", return_value="/usr/bin/lsb_release"), \
             patch("subprocess.run", return_value=proc):
            result = PardusVerifier._read_lsb_release()
        assert result["distributor_id"] == "Pardus"
        assert result["release"] == "23.2"
        assert result["codename"] == "yirmiuc"

    def test_lsb_not_installed(self):
        with patch("shutil.which", return_value=None):
            result = PardusVerifier._read_lsb_release()
        assert result == {}

    def test_lsb_timeout(self):
        import subprocess
        with patch("shutil.which", return_value="/usr/bin/lsb_release"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 10)):
            result = PardusVerifier._read_lsb_release()
        assert result == {}

    def test_lsb_nonzero_exit(self):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/lsb_release"), \
             patch("subprocess.run", return_value=proc):
            result = PardusVerifier._read_lsb_release()
        assert result == {}


class TestCollectHardwareInfo:
    """Tests for _collect_hardware_info."""

    @patch("os.cpu_count", return_value=8)
    @patch("platform.processor", return_value="x86_64")
    @patch("platform.machine", return_value="x86_64")
    @patch("platform.version", return_value="#1 SMP")
    @patch("platform.release", return_value="6.1.0-pardus")
    def test_hardware_with_psutil(self, *_):
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value = MagicMock(total=8589934592)
        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = PardusVerifier._collect_hardware_info()
        assert result["kernel"] == "6.1.0-pardus"
        assert result["architecture"] == "x86_64"
        assert result["cpu_count"] == 8
        assert result["total_ram_bytes"] == 8589934592

    @patch("os.cpu_count", return_value=2)
    @patch("platform.processor", return_value="")
    @patch("platform.machine", return_value="aarch64")
    @patch("platform.version", return_value="#1")
    @patch("platform.release", return_value="5.15.0")
    def test_hardware_fallback_meminfo(self, *_):
        meminfo = "MemTotal:       16384000 kB\nMemFree:        8000000 kB\n"
        with patch.dict("sys.modules", {"psutil": None}), \
             patch("builtins.open", mock_open(read_data=meminfo)):
            # psutil import will fail if sys.modules maps it to None;
            # handle by patching the import to raise ImportError
            import importlib
            result = PardusVerifier._collect_hardware_info()
        assert result["architecture"] == "aarch64"
        assert result["processor"] == "Unknown"


class TestCheckPardusPackages:
    """Tests for _check_pardus_packages."""

    @pytest.fixture
    def verifier(self):
        return PardusVerifier()

    def test_dpkg_not_found(self, verifier):
        with patch("shutil.which", return_value=None):
            result = verifier._check_pardus_packages()
        assert result == []

    def test_package_installed(self, verifier):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "install ok installed"
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=proc):
            result = verifier._check_pardus_packages()
        assert all(p["status"] == "installed" for p in result)

    def test_package_not_installed(self, verifier):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=proc):
            result = verifier._check_pardus_packages()
        assert all(p["status"] == "not-installed" for p in result)

    def test_package_error(self, verifier):
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", side_effect=Exception("fail")):
            result = verifier._check_pardus_packages()
        assert all(p["status"] == "error" for p in result)


class TestListPardusPackages:
    """Tests for _list_pardus_packages."""

    def test_filters_pardus_prefix(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "pardus-software\npardus-about\nfirefox\nlibreoffice\npardus-store\n"
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=proc):
            result = PardusVerifier._list_pardus_packages()
        assert result == ["pardus-software", "pardus-about", "pardus-store"]

    def test_no_dpkg(self):
        with patch("shutil.which", return_value=None):
            result = PardusVerifier._list_pardus_packages()
        assert result == []

    def test_nonzero_exit(self):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=proc):
            result = PardusVerifier._list_pardus_packages()
        assert result == []


class TestDetectDesktopEnvironment:
    """Tests for _detect_desktop_environment."""

    def test_xdg_current_desktop(self):
        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "XFCE", "DESKTOP_SESSION": ""}):
            assert PardusVerifier._detect_desktop_environment() == "XFCE"

    def test_desktop_session_fallback(self):
        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "", "DESKTOP_SESSION": "gnome"}):
            assert PardusVerifier._detect_desktop_environment() == "gnome"

    def test_unknown_fallback(self):
        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "", "DESKTOP_SESSION": ""}, clear=False):
            result = PardusVerifier._detect_desktop_environment()
            assert result in ("Unknown", "")


class TestFormatAsText:
    """Tests for format_as_text."""

    @pytest.fixture
    def verifier(self):
        return PardusVerifier()

    def test_no_data_returns_message(self, verifier):
        text = verifier.format_as_text()
        assert "No verification data" in text

    def test_formats_pardus_report(self, verifier):
        report = {
            "is_pardus": True,
            "timestamp": "2026-01-01T12:00:00",
            "hostname": "pardus-test",
            "os_release": {"ID": "pardus", "PRETTY_NAME": "Pardus 23.2"},
            "lsb_release": {"distributor_id": "Pardus"},
            "hardware": {
                "kernel": "6.1.0", "architecture": "x86_64",
                "processor": "x86_64", "cpu_count": 4,
                "total_ram_bytes": 8589934592,
            },
            "desktop_environment": "XFCE",
            "pardus_services": [
                {"name": "pardus-software", "status": "installed"},
            ],
            "pardus_packages": ["pardus-software", "pardus-about"],
        }
        text = verifier.format_as_text(report)
        assert "Is Pardus" in text
        assert "Yes" in text
        assert "pardus-software" in text
        assert "XFCE" in text

    def test_uses_cached_report(self, verifier):
        verifier._cache = {
            "is_pardus": False,
            "timestamp": "2026-06-01",
            "hostname": "test",
            "os_release": {},
            "lsb_release": {},
            "hardware": {"kernel": "5.10", "architecture": "arm64",
                         "processor": "arm", "cpu_count": 2,
                         "total_ram_bytes": 0},
            "desktop_environment": "Unknown",
            "pardus_services": [],
            "pardus_packages": [],
        }
        text = verifier.format_as_text()
        assert "No" in text  # is_pardus = False → "No"
