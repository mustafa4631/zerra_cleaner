import os
import json
import locale
import logging

logger = logging.getLogger("gk-healter.i18n")


class I18nManager:
    """
    Manages application translations using JSON files.
    Supports system language detection and manual language switching.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(I18nManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, language='auto'):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.locale_dir = os.path.join(os.path.dirname(__file__), "locale")
        self.current_language = language
        self.translations = {}
        self.default_language = 'en'

        self.load_language(language)
        self._initialized = True

    def load_language(self, language):
        """Loads the specified language or detects system language if 'auto'."""
        if language == 'auto':
            try:
                sys_lang = locale.getlocale()[0]
                if sys_lang and sys_lang.startswith('tr'):
                    target_lang = 'tr'
                else:
                    target_lang = 'en'
            except Exception:
                target_lang = 'en'
        else:
            target_lang = language

        file_path = os.path.join(self.locale_dir, f"{target_lang}.json")

        # Fallback to English if file doesn't exist
        if not os.path.exists(file_path):
            file_path = os.path.join(self.locale_dir, f"{self.default_language}.json")
            target_lang = self.default_language

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
                self.current_language = target_lang
        except Exception as e:
            logger.error("Failed to load translations for %s: %s", target_lang, e)
            self.translations = {}

    def get_text(self, key, default=None):
        """Returns the translated text for a given key."""
        return self.translations.get(key, default if default is not None else key)

# Helper function for translation
def _(key, default=None):
    return I18nManager().get_text(key, default)
