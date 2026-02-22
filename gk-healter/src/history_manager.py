import os
import json
import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger("gk-healter.history")


class HistoryManager:
    """
    Manages the cleaning history by saving and retrieving records from a JSON file.
    The history is stored in ~/.local/share/gk-healter/history.json
    """
    def __init__(self):
        self.history_dir = os.path.expanduser("~/.local/share/gk-healter")
        self.history_file = os.path.join(self.history_dir, "history.json")
        self._ensure_dir_exists()

    def _ensure_dir_exists(self):
        """Ensures the storage directory exists."""
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir, exist_ok=True)

    def add_entry(self, categories: List[str], total_freed_str: str, status: str):
        """
        Adds a new cleaning entry to the history.
        :param categories: List of category names cleaned.
        :param total_freed_str: Formatted string of total space freed.
        :param status: Result status (Başarılı, Kısmi, Başarısız).
        """
        entry = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "categories": ", ".join(categories),
            "total_freed": total_freed_str,
            "status": status
        }

        history = self.get_all_entries()
        history.insert(0, entry)  # Newest first

        # Limit history to last 100 entries to keep it light
        history = history[:100]

        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error("Failed to save history: %s", e)

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Retrieves all history entries."""
        if not os.path.exists(self.history_file):
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read history: %s", e)
            return []
