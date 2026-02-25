import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, GLib

from src.logger import setup_logging
from src.settings_manager import SettingsManager
from src.i18n_manager import I18nManager
from src.ui import MainWindow


def main():
    """Application entry point."""
    # Set application name for WMClass
    GLib.set_prgname('io.github.gkdevelopers.GKHealter')

    # Initialize logging first
    setup_logging()

    # Initialize settings and i18n
    settings = SettingsManager()
    I18nManager(settings.get("language"))

    MainWindow()
    Gtk.main()


if __name__ == "__main__":
    main()
