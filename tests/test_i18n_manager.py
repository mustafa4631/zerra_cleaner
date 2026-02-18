"""
GK Healter – Test Suite: i18n_manager.py
"""

import os
import json
import pytest
from unittest.mock import patch
from gk_healter_tests.helpers import src_import

i18n_mod = src_import("i18n_manager")
I18nManager = i18n_mod.I18nManager


class TestI18nManager:
    """Tests for the I18nManager singleton."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton before each test."""
        I18nManager._instance = None
        yield
        I18nManager._instance = None

    def test_loads_english_by_default(self):
        mgr = I18nManager("en")
        assert mgr.current_language == "en"
        assert mgr.get_text("app_title") == "GK Healter"

    def test_loads_turkish(self):
        mgr = I18nManager("tr")
        assert mgr.current_language == "tr"
        assert mgr.get_text("btn_clean") == "Temizle"

    def test_auto_detects_language(self):
        with patch("locale.getdefaultlocale", return_value=("tr_TR", "UTF-8")):
            mgr = I18nManager("auto")
            assert mgr.current_language == "tr"

    def test_auto_defaults_english_for_non_turkish(self):
        with patch("locale.getdefaultlocale", return_value=("de_DE", "UTF-8")):
            mgr = I18nManager("auto")
            assert mgr.current_language == "en"

    def test_auto_defaults_english_on_exception(self):
        with patch("locale.getdefaultlocale", side_effect=Exception("fail")):
            mgr = I18nManager("auto")
            assert mgr.current_language == "en"

    def test_fallback_to_english_for_unknown_lang(self):
        mgr = I18nManager("zz")  # no zz.json exists
        assert mgr.current_language == "en"
        assert mgr.get_text("app_title") == "GK Healter"

    def test_get_text_returns_key_if_missing(self):
        mgr = I18nManager("en")
        assert mgr.get_text("nonexistent_key_xyz") == "nonexistent_key_xyz"

    def test_get_text_returns_custom_default(self):
        mgr = I18nManager("en")
        assert mgr.get_text("nonexistent_key", "fallback") == "fallback"

    def test_singleton_pattern(self):
        mgr1 = I18nManager("en")
        mgr2 = I18nManager("tr")  # should not re-init
        assert mgr1 is mgr2
        assert mgr1.current_language == "en"  # first init wins

    def test_load_language_switch(self):
        mgr = I18nManager("en")
        assert mgr.get_text("btn_clean") == "Clean"
        mgr.load_language("tr")
        assert mgr.get_text("btn_clean") == "Temizle"
        assert mgr.current_language == "tr"


class TestTranslationHelper:
    """Tests for the _() helper function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        I18nManager._instance = None
        yield
        I18nManager._instance = None

    def test_helper_returns_translation(self):
        _ = i18n_mod._
        I18nManager("en")
        assert _("app_title") == "GK Healter"

    def test_helper_returns_key_for_missing(self):
        _ = i18n_mod._
        I18nManager("en")
        assert _("no_such_key_abc") == "no_such_key_abc"


class TestLocaleFileIntegrity:
    """Verify en.json and tr.json have matching keys."""

    def test_all_en_keys_exist_in_tr(self):
        locale_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gk-healter", "src", "locale",
        )
        with open(os.path.join(locale_dir, "en.json"), "r") as f:
            en_keys = set(json.load(f).keys())
        with open(os.path.join(locale_dir, "tr.json"), "r") as f:
            tr_keys = set(json.load(f).keys())

        missing_in_tr = en_keys - tr_keys
        assert missing_in_tr == set(), f"Keys in en.json missing from tr.json: {missing_in_tr}"

    def test_all_tr_keys_exist_in_en(self):
        locale_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gk-healter", "src", "locale",
        )
        with open(os.path.join(locale_dir, "en.json"), "r") as f:
            en_keys = set(json.load(f).keys())
        with open(os.path.join(locale_dir, "tr.json"), "r") as f:
            tr_keys = set(json.load(f).keys())

        extra_in_tr = tr_keys - en_keys
        assert extra_in_tr == set(), f"Keys in tr.json not in en.json: {extra_in_tr}"
