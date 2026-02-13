import os
import gi
import threading
from typing import List, Dict, Any, Optional

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from src.cleaner import SystemCleaner
from src.history_manager import HistoryManager
from src.settings_manager import SettingsManager
from src.auto_maintenance_manager import AutoMaintenanceManager
from src.i18n_manager import _, I18nManager
import datetime

class MainWindow(Gtk.Window):
    """
    Main application window for the GK Healter.
    Handles UI events, signal connections, and interacts with the SystemCleaner logic.
    """
    def __init__(self) -> None:
        """
        Initializes the MainWindow by loading the UI from XML and connecting signals.
        """
        # We don't call super() init here because we are loading from XML
        # Instead, we pull the window object from the builder.
        
        self.cleaner: SystemCleaner = SystemCleaner()
        self.settings_manager: SettingsManager = SettingsManager()
        self.history_manager: HistoryManager = HistoryManager()
        self.auto_maintenance_manager: AutoMaintenanceManager = AutoMaintenanceManager(self.settings_manager, self.history_manager)
        self.scan_data: List[Dict[str, Any]] = []
        self.current_cleaning_info: Dict[str, Any] = {}
        self.is_auto_maintenance_run: bool = False
        self.is_cleaning_in_progress: bool = False

        # Load XML
        builder = Gtk.Builder()
        ui_path = os.path.join(os.path.dirname(__file__), "../resources/main_window.ui")
        builder.add_from_file(ui_path)

        # Get Main Window
        self.window: Gtk.Window = builder.get_object("main_window")
        
        # Set Application Icon (works for both Flatpak and system install)
        try:
            # Try themed icon first (Flatpak uses this)
            icon_theme = Gtk.IconTheme.get_default()
            if icon_theme.has_icon("io.github.gkdevelopers.GKHealter"):
                self.window.set_icon_name("io.github.gkdevelopers.GKHealter")
            else:
                # Fallback to local file
                svg_icon_path = os.path.join(os.path.dirname(__file__), "../resources/gk-healter.svg")
                png_icon_path = os.path.join(os.path.dirname(__file__), "../resources/gk-healter.png")
                
                if os.path.exists(svg_icon_path):
                    self.window.set_icon_from_file(svg_icon_path)
                elif os.path.exists(png_icon_path):
                    self.window.set_icon_from_file(png_icon_path)
        except Exception as e:
            print(f"Error setting icon: {e}")

        self.window.connect("destroy", Gtk.main_quit)
        
        # Get Objects
        self.main_stack: Gtk.Stack = builder.get_object("main_stack")
        self.info_bar: Gtk.InfoBar = builder.get_object("info_bar")
        self.info_label: Gtk.Label = builder.get_object("info_label")
        self.treeview: Gtk.TreeView = builder.get_object("treeview")
        self.store: Gtk.ListStore = builder.get_object("file_list_store")
        self.summary_label: Gtk.Label = builder.get_object("summary_label")
        self.btn_scan: Gtk.Button = builder.get_object("btn_scan")
        self.btn_clean: Gtk.Button = builder.get_object("btn_clean")
        self.btn_about: Gtk.Button = builder.get_object("btn_about")

        # History Objects
        self.history_treeview: Gtk.TreeView = builder.get_object("history_treeview")
        self.history_store: Gtk.ListStore = builder.get_object("history_list_store")
        self.notebook: Gtk.Notebook = builder.get_object("notebook")
        self.btn_settings: Gtk.Button = builder.get_object("btn_settings")

        # Settings Objects
        self.switch_auto_maintenance: Gtk.Switch = builder.get_object("switch_auto_maintenance")
        self.combo_frequency: Gtk.ComboBoxText = builder.get_object("combo_frequency")
        self.spin_idle: Gtk.SpinButton = builder.get_object("spin_idle")
        self.switch_disk_threshold: Gtk.Switch = builder.get_object("switch_disk_threshold")
        self.spin_disk_percent: Gtk.SpinButton = builder.get_object("spin_disk_percent")
        self.switch_ac_power: Gtk.Switch = builder.get_object("switch_ac_power")
        self.switch_notify: Gtk.Switch = builder.get_object("switch_notify")
        self.lbl_last_maintenance: Gtk.Label = builder.get_object("lbl_last_maintenance")
        self.btn_back: Gtk.Button = builder.get_object("btn_back")
        self.box_auto_settings: Gtk.Box = builder.get_object("box_auto_settings")
        self.combo_language: Gtk.ComboBoxText = builder.get_object("combo_language")

        # Translation labels (need IDs from UI file)
        self.lbl_settings_language: Gtk.Label = builder.get_object("lbl_settings_language")
        self.lbl_language_select: Gtk.Label = builder.get_object("lbl_language_select")
        self.lbl_last_maintenance_title: Gtk.Label = builder.get_object("lbl_last_maintenance_title")
        
        # Other translated labels
        self.lbl_settings_title: Gtk.Label = builder.get_object("lbl_settings_title")
        self.lbl_auto_maintenance_title: Gtk.Label = builder.get_object("lbl_auto_maintenance_title")
        self.lbl_auto_maintenance_desc: Gtk.Label = builder.get_object("lbl_auto_maintenance_desc")
        self.lbl_scheduling_title: Gtk.Label = builder.get_object("lbl_scheduling_title")
        self.lbl_frequency_title: Gtk.Label = builder.get_object("lbl_frequency_title")
        self.lbl_conditions_title: Gtk.Label = builder.get_object("lbl_conditions_title")
        self.lbl_idle_title: Gtk.Label = builder.get_object("lbl_idle_title")
        self.lbl_minutes_suffix: Gtk.Label = builder.get_object("lbl_minutes_suffix")
        self.lbl_ac_power_title: Gtk.Label = builder.get_object("lbl_ac_power_title")
        self.lbl_notifications_title: Gtk.Label = builder.get_object("lbl_notifications_title")
        self.lbl_notify_done_title: Gtk.Label = builder.get_object("lbl_notify_done_title")
        self.expander_advanced: Gtk.Expander = builder.get_object("expander_advanced")
        self.lbl_disk_threshold_title: Gtk.Label = builder.get_object("lbl_disk_threshold_title")

        # Get Dialogs
        self.about_dialog: Gtk.AboutDialog = builder.get_object("about_dialog")
        self.clean_confirm_dialog: Gtk.MessageDialog = builder.get_object("clean_confirm_dialog")

        # Status Icon (programmatic addition to InfoBar)
        self.status_icon = Gtk.Image()
        info_content = self.info_bar.get_content_area()
        # Add icon at the start of the box
        info_content.pack_start(self.status_icon, False, False, 0)
        info_content.reorder_child(self.status_icon, 0)
        self.status_icon.show()

        # Connect Signals
        builder.connect_signals(self)
        
        # Initial History Load
        self.populate_history()

        # Translate UI
        self._translate_ui()

        # Load Settings UI
        self._sync_settings_ui()

        self.window.show_all()

        # Check for auto maintenance after a short delay
        GLib.timeout_add(1000, self.check_auto_maintenance)

    def _translate_ui(self) -> None:
        """Updates all UI text elements using the translation manager."""
        self.window.set_title(_("app_title"))
        # self.header_bar.set_title(_("header_title")) # HeaderBar title is usually set via property
        self.btn_about.set_tooltip_text(_("btn_about"))
        self.btn_settings.set_tooltip_text(_("tooltip_settings"))
        
        self.info_label.set_text(_("info_ready"))
        
        # Tabs
        self.notebook.get_nth_page(0).get_parent().set_tab_label_text(self.notebook.get_nth_page(0), _("tab_clean"))
        self.notebook.get_nth_page(1).get_parent().set_tab_label_text(self.notebook.get_nth_page(1), _("tab_history"))

        # TreeViews
        self.treeview.get_column(0).set_title(_("col_select"))
        self.treeview.get_column(1).set_title(_("col_category"))
        self.treeview.get_column(2).set_title(_("col_description"))
        self.treeview.get_column(3).set_title(_("col_size"))
        
        self.history_treeview.get_column(0).set_title(_("col_date"))
        self.history_treeview.get_column(1).set_title(_("col_category"))
        self.history_treeview.get_column(2).set_title(_("col_size"))
        self.history_treeview.get_column(3).set_title(_("col_status"))

        # Main Buttons
        self.btn_scan.set_label(_("btn_scan"))
        self.btn_clean.set_label(_("btn_clean"))

        # Settings Page
        self.btn_back.set_tooltip_text(_("tooltip_back", "Geri Dön"))
        # self.lbl_settings_title.set_text(_("settings_title")) # Need ID

        # Language section labels are updated via sync_settings_ui or here
        self.lbl_settings_language.set_text(_("settings_language"))
        self.lbl_language_select.set_text(_("settings_language")) 
        self.lbl_last_maintenance_title.set_text(_("settings_last_maintenance"))

        self.lbl_settings_title.set_text(_("settings_title"))
        self.lbl_auto_maintenance_title.set_text(_("settings_auto_maintenance"))
        self.lbl_auto_maintenance_desc.set_text(_("settings_auto_desc"))
        self.lbl_scheduling_title.set_text(_("settings_scheduling"))
        self.lbl_frequency_title.set_text(_("settings_frequency"))
        self.lbl_conditions_title.set_text(_("settings_conditions"))
        self.lbl_idle_title.set_text(_("settings_idle"))
        self.lbl_minutes_suffix.set_text(_("minutes_suffix", "dk"))
        self.lbl_ac_power_title.set_text(_("settings_ac_power"))
        self.lbl_notifications_title.set_text(_("settings_notifications"))
        self.lbl_notify_done_title.set_text(_("settings_notify_done"))
        if self.expander_advanced:
            self.expander_advanced.set_label(_("advanced_options"))
        self.lbl_disk_threshold_title.set_text(_("settings_disk_threshold"))

        # Combo Frequency items (manual translation)
        active_freq = self.combo_frequency.get_active_id()
        self.combo_frequency.remove_all()
        self.combo_frequency.append("7", _("freq_7"))
        self.combo_frequency.append("30", _("freq_30"))
        self.combo_frequency.append("180", _("freq_180"))
        self.combo_frequency.append("365", _("freq_365"))
        self.combo_frequency.set_active_id(active_freq)

        # Sync combo items
        self.combo_language.remove_all()
        self.combo_language.append("auto", _("lang_auto"))
        self.combo_language.append("tr", _("lang_tr"))
        self.combo_language.append("en", _("lang_en"))
        self.combo_language.set_active_id(self.settings_manager.get("language"))

        # About Dialog
        self.about_dialog.set_property("program_name", _("app_title"))
        self.about_dialog.set_property("copyright", "© 2026 GK Developers")
        self.about_dialog.set_property("logo", self.window.get_icon())

        # Confirm Dialog
        self.clean_confirm_dialog.set_property("text", _("confirm_title"))
        self.clean_confirm_dialog.set_title(_("confirm_title"))

    def _sync_settings_ui(self) -> None:
        """Syncs the settings UI with values from SettingsManager."""
        self.switch_auto_maintenance.set_active(self.settings_manager.get("auto_maintenance_enabled"))
        
        freq = self.settings_manager.get("maintenance_frequency_days")
        self.combo_frequency.set_active_id(str(freq))

        self.spin_idle.set_value(self.settings_manager.get("idle_threshold_minutes"))
        self.switch_disk_threshold.set_active(self.settings_manager.get("disk_threshold_enabled"))
        self.spin_disk_percent.set_value(self.settings_manager.get("disk_threshold_percent"))
        self.switch_ac_power.set_active(self.settings_manager.get("check_ac_power"))
        self.switch_notify.set_active(self.settings_manager.get("notify_on_completion"))
        
        last_date = self.settings_manager.get("last_maintenance_date")
        if last_date:
            self.lbl_last_maintenance.set_text(last_date)
        else:
            self.lbl_last_maintenance.set_text(_("never_run"))

        self.combo_language.set_active_id(self.settings_manager.get("language"))
        self._update_settings_visibility()

    def _update_settings_visibility(self) -> None:
        """Shows/hides detailed maintenance settings based on the master switch."""
        is_enabled = self.switch_auto_maintenance.get_active()
        self.box_auto_settings.set_visible(is_enabled)

    def check_auto_maintenance(self) -> bool:
        """Periodic check for auto-maintenance conditions every 1 minute."""
        if self.is_cleaning_in_progress or self.is_auto_maintenance_run:
            # Re-schedule check if already busy
            GLib.timeout_add_seconds(60, self.check_auto_maintenance)
            return False

        if self.auto_maintenance_manager.can_run_maintenance(force_disk_check=True):
            print("Starting intelligence auto-maintenance...")
            self.is_auto_maintenance_run = True
            
            # Run in thread
            thread = threading.Thread(target=self.run_auto_maintenance_thread)
            thread.daemon = True
            thread.start()
        
        # Change to 1 minute interval after first check
        GLib.timeout_add_seconds(60, self.check_auto_maintenance)
        return False # Stop current timer

    def run_auto_maintenance_thread(self) -> None:
        """Executes auto maintenance in a background thread."""
        res = self.auto_maintenance_manager.run_maintenance()
        GLib.idle_add(self.on_auto_maintenance_finished, res)

    def on_auto_maintenance_finished(self, res: Optional[dict]) -> None:
        """Callback when auto maintenance is complete."""
        self.is_auto_maintenance_run = False
        if res:
            if self.settings_manager.get("notify_on_completion"):
                self.show_notification(_("auto_maintenance_title"), 
                                     _("auto_maintenance_finished_msg").format(res['freed']))
            self.populate_history()
            self._sync_settings_ui()

    def on_settings_clicked(self, widget: Gtk.Button) -> None:
        self._sync_settings_ui()
        self.main_stack.set_visible_child_name("page_settings")

    def on_back_clicked(self, widget: Gtk.Button) -> None:
        self.main_stack.set_visible_child_name("page_main")

    def on_auto_maintenance_toggled(self, switch: Gtk.Switch, gparam: Any) -> None:
        self.settings_manager.set("auto_maintenance_enabled", switch.get_active())
        self._update_settings_visibility()

    def on_frequency_changed(self, combo: Gtk.ComboBoxText) -> None:
        active_id = combo.get_active_id()
        if active_id:
            self.settings_manager.set("maintenance_frequency_days", int(active_id))

    def on_idle_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings_manager.set("idle_threshold_minutes", int(spin.get_value()))

    def on_disk_threshold_toggled(self, switch: Gtk.Switch, gparam: Any) -> None:
        self.settings_manager.set("disk_threshold_enabled", switch.get_active())

    def on_disk_percent_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings_manager.set("disk_threshold_percent", int(spin.get_value()))

    def on_ac_power_toggled(self, switch: Gtk.Switch, gparam: Any) -> None:
        self.settings_manager.set("check_ac_power", switch.get_active())

    def on_notify_toggled(self, switch: Gtk.Switch, gparam: Any) -> None:
        self.settings_manager.set("notify_on_completion", switch.get_active())

    def on_language_changed(self, combo: Gtk.ComboBoxText) -> None:
        active_id = combo.get_active_id()
        if active_id and active_id != self.settings_manager.get("language"):
            self.settings_manager.set("language", active_id)
            # Re-load language in manager
            I18nManager().load_language(active_id)
            # Refresh UI
            self._translate_ui()
            # Notify user
            self.info_bar.set_message_type(Gtk.MessageType.INFO)
            self.info_label.set_text(_("msg_reboot_required"))
            self.info_bar.show()

    def show_notification(self, title: str, message: str) -> None:
        """Displays a system notification."""
        try:
            import subprocess
            subprocess.run(['notify-send', title, message])
        except Exception:
            pass

    def populate_history(self) -> None:
        """
        Loads cleaning history from the HistoryManager and populates the history treeview.
        """
        self.history_store.clear()
        entries = self.history_manager.get_all_entries()
        for entry in entries:
            self.history_store.append([
                entry.get("date", ""),
                entry.get("categories", ""),
                entry.get("total_freed", ""),
                entry.get("status", "")
            ])

    def on_cell_toggled(self, widget: Gtk.CellRendererToggle, path: str) -> None:
        """
        Callback for when a checkbox in the treeview is toggled.
        Updates the model and recalculates the summary.
        """
        self.store[path][0] = not self.store[path][0]
        self.update_summary()

    def update_summary(self) -> None:
        """
        Calculates the total size of selected items and updates the summary label.
        Controls the clean button sensitivity.
        """
        total_bytes = 0
        for row in self.store:
            if row[0]: # If checked
                total_bytes += row[4]
        
        mb = total_bytes / (1024 * 1024)
        self.summary_label.set_text(_("summary_total").format(f"{mb:.2f}"))
        self.btn_clean.set_sensitive(total_bytes > 0)

    def on_scan_clicked(self, widget: Gtk.Button) -> None:
        """
        Callback for the 'Scan' button. Initiates the system scan in a separate thread.
        """
        self.btn_scan.set_sensitive(False)
        self.store.clear()
        self.info_label.set_text(_("info_scanning"))
        self.info_bar.set_message_type(Gtk.MessageType.INFO)
        
        # Start scanning in a separate thread to keep UI responsive
        thread = threading.Thread(target=self.run_scan_thread)
        thread.daemon = True
        thread.start()

    def run_scan_thread(self) -> None:
        """
        Executed in a background thread. Performs the scan.
        """
        results = self.cleaner.scan()
        GLib.idle_add(self.on_scan_finished, results)

    def on_scan_finished(self, results: List[Dict[str, Any]]) -> None:
        """
        Callback invoked on the main thread when scanning is complete.
        Populates the treeview with results.
        """
        self.store.clear()
        for item in results:
            # Checkbox, Category, Desc, Size Str, Size Bytes, Path, System
            self.store.append([
                True, 
                item['category'], 
                item['desc'], 
                item['size_str'], 
                item['size_bytes'],
                item['path'],
                item['system']
            ])
        
        self.update_summary()
        self.btn_scan.set_sensitive(True)
        
        if not results:
            self.info_bar.set_message_type(Gtk.MessageType.WARNING)
            self.status_icon.set_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.BUTTON)
            self.info_label.set_markup(f"<b>{_('info_no_items')}</b>")
        else:
            self.info_bar.set_message_type(Gtk.MessageType.INFO)
            self.status_icon.set_from_icon_name("dialog-information-symbolic", Gtk.IconSize.BUTTON)
            self.info_label.set_markup(f"<b>{_('info_scan_completed')}</b>")

    def on_clean_clicked(self, widget: Gtk.Button) -> None:
        """
        Callback for the 'Clean' button. Confirms action and starts cleaning.
        """
        if self.is_cleaning_in_progress:
            self.info_bar.set_message_type(Gtk.MessageType.WARNING)
            self.status_icon.set_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.BUTTON)
            self.info_label.set_markup(f"<span weight='bold'>{_('msg_cleaning_in_progress')}</span>")
            return

        to_clean = []
        for row in self.store:
            if row[0]: # Checked
                to_clean.append({
                    'path': row[5],
                    'system': row[6]
                })

        if not to_clean:
            self.info_bar.set_message_type(Gtk.MessageType.WARNING)
            self.status_icon.set_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.BUTTON)
            self.info_label.set_markup(f"<span weight='bold'>{_('msg_no_selection')}</span>")
            return

        # Update dialog text
        self.clean_confirm_dialog.format_secondary_text(
            _("confirm_text").format(len(to_clean))
        )
        
        # Store current cleaning info for history logging
        categories = []
        total_bytes = 0
        for row in self.store:
            if row[0]:
                categories.append(row[1])
                total_bytes += row[4]
        
        from src.utils import format_size
        self.current_cleaning_info = {
            'categories': categories,
            'total_freed_str': format_size(total_bytes)
        }

        response = self.clean_confirm_dialog.run()
        self.clean_confirm_dialog.hide()
        
        if response == Gtk.ResponseType.OK:
            self.is_cleaning_in_progress = True
            self.btn_clean.set_sensitive(False)
            self.btn_scan.set_sensitive(False)
            self.info_label.set_text(_("info_cleaning"))
            self.info_bar.set_message_type(Gtk.MessageType.INFO)
            self.status_icon.set_from_icon_name("process-working-symbolic", Gtk.IconSize.BUTTON)
            
            # Threaded clean
            thread = threading.Thread(target=self.run_clean_thread, args=(to_clean,))
            thread.daemon = True
            thread.start()

    def run_clean_thread(self, to_clean: List[Dict[str, Any]]) -> None:
        """
        Executed in a background thread. Performs the cleaning operation.
        """
        success_count, fail_count, errors = self.cleaner.clean(to_clean)
        GLib.idle_add(self.on_clean_finished, success_count, fail_count, errors)

    def on_clean_finished(self, success_count: int, fail_count: int, errors: List[str]) -> None:
        """
        Callback invoked on the main thread when cleaning is complete.
        Refreshes the scan and shows errors if any.
        """
        self.is_cleaning_in_progress = False
        self.on_scan_clicked(None) # Refresh
        
        if fail_count > 0:
            self.info_bar.set_message_type(Gtk.MessageType.ERROR)
            self.status_icon.set_from_icon_name("dialog-error-symbolic", Gtk.IconSize.BUTTON)
            error_text = "\n".join(errors)
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("msg_error_title"),
            )
            dialog.format_secondary_text(_("msg_errors_detail").format(fail_count, error_text))
            dialog.run()
            dialog.destroy()
            self.info_label.set_markup(_("info_cleaning_failed_msg").format(fail_count))
            status = _("status_partial") if success_count > 0 else _("status_failed")
        else:
            self.info_bar.set_message_type(Gtk.MessageType.INFO)
            self.status_icon.set_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.BUTTON)
            self.info_label.set_markup(f"<b>{_('info_cleaning_success')}</b> {success_count} {_('actions_done')}")
            status = _("status_success")

        # Log to history
        if self.current_cleaning_info:
            is_auto = self.current_cleaning_info.get('is_auto', False)
            
            cats = list(self.current_cleaning_info['categories'])
            if is_auto:
                cats.append("Otomatik bakım")

            self.history_manager.add_entry(
                cats,
                self.current_cleaning_info['total_freed_str'],
                status
            )
            
            if is_auto:
                # Update last maintenance date
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.settings_manager.set("last_maintenance_date", now_str)
                self.is_auto_maintenance_run = False

            self.populate_history()
            self.current_cleaning_info = {}

    def on_about_clicked(self, widget: Gtk.Button) -> None:
        """
        Callback for the 'About' button. Shows the about dialog.
        """
        self.about_dialog.run()
        self.about_dialog.hide()
