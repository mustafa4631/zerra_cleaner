import os
import json
import datetime

class SettingsManager:
    """
    Manages application settings, including automatic maintenance configuration.
    Stored in ~/.config/gk-healter/settings.json
    """
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/gk-healter")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.defaults = {
            "auto_maintenance_enabled": False,
            "last_maintenance_date": None,
            "maintenance_frequency_days": 7,
            "idle_threshold_minutes": 15,
            "disk_threshold_enabled": False,
            "disk_threshold_percent": 90,
            "check_ac_power": True,
            "notify_on_completion": False,
            "language": "auto"
        }
        self.settings = self.defaults.copy()
        self._load_settings()

    def _ensure_dir_exists(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

    def _load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"Failed to load settings: {e}")

    def save_settings(self):
        self._ensure_dir_exists()
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def is_maintenance_due(self) -> bool:
        """Checks if monthly maintenance is due."""
        if not self.get("auto_maintenance_enabled"):
            return False
            
        last_date_str = self.get("last_maintenance_date")
        if not last_date_str:
            return True # Never run, so it's due
            
        try:
            last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            diff = now - last_date
            return diff.days >= self.get("maintenance_frequency_days")
        except Exception as e:
            print(f"Error parsing date: {e}")
            return True
