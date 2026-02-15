"""
GK Healter – Main UI Module
All layout is defined in resources/main_window.ui (GTK Builder XML).
This module handles signal connections, business logic, and dynamic content only.
"""

import os
import threading
import datetime
from typing import List, Dict, Any, Optional

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango

from src.cleaner import SystemCleaner
from src.history_manager import HistoryManager
from src.settings_manager import SettingsManager
from src.auto_maintenance_manager import AutoMaintenanceManager
from src.i18n_manager import _, I18nManager
from src.health_engine import HealthEngine
from src.service_analyzer import ServiceAnalyzer
from src.log_analyzer import LogAnalyzer
from src.disk_analyzer import DiskAnalyzer
from src.recommendation_engine import RecommendationEngine
from src.ai_engine import AIEngine
from src.utils import format_size


class MainWindow:
    """
    Application controller.  Every visible widget lives in the .ui file;
    this class only wires signals and feeds data into those widgets.
    """

    # ── Construction ─────────────────────────────────────────────────────────
    def __init__(self) -> None:
        # Back-end services
        self.cleaner = SystemCleaner()
        self.settings_manager = SettingsManager()
        self.history_manager = HistoryManager()
        self.auto_maintenance_manager = AutoMaintenanceManager(
            self.settings_manager, self.history_manager
        )
        self.health_engine = HealthEngine()
        self.service_analyzer = ServiceAnalyzer()
        self.log_analyzer = LogAnalyzer()
        self.disk_analyzer = DiskAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        self.ai_engine = AIEngine()

        # State
        self.scan_data: List[Dict[str, Any]] = []
        self.is_cleaning_in_progress: bool = False
        self._health_timer_id: Optional[int] = None

        # Load the builder file
        self.builder = Gtk.Builder()
        ui_path = os.path.join(
            os.path.dirname(__file__), "..", "resources", "main_window.ui"
        )
        self.builder.add_from_file(ui_path)

        # Connect signals declared in XML to handler methods
        self.builder.connect_signals(self)

        # Grab references to widgets we will update at runtime
        self._bind_widgets()

        # Apply minimal CSS that cannot be expressed in XML
        self._apply_css()

        # Populate combos, restore saved settings, load history
        self._init_settings_ui()
        self._load_history_into_view()

        # Apply i18n translations to all hardcoded XML labels
        self._apply_translations()

        # Set the application icon
        self._set_app_icon()

        # Show window and start background monitors
        self.window.show_all()
        # Re-hide auto-settings box if needed (show_all overrides)
        if not self.settings_manager.get("auto_maintenance_enabled"):
            self.box_auto_settings.set_visible(False)

        self.health_engine.start_monitoring()
        self._start_health_timer()
        self._refresh_dashboard()

    # ── Widget binding (from builder) ────────────────────────────────────────
    def _bind_widgets(self) -> None:
        """Retrieve widget references from the builder by their XML IDs."""
        g = self.builder.get_object

        # Main window
        self.window: Gtk.Window = g("main_window")
        self.window.connect("destroy", self.on_window_destroy)

        # Stack
        self.content_stack: Gtk.Stack = g("content_stack")

        # ── Dashboard ──
        self.lbl_welcome: Gtk.Label = g("lbl_welcome")
        self.lbl_welcome_sub: Gtk.Label = g("lbl_welcome_sub")
        self.lbl_score_value: Gtk.Label = g("lbl_score_value")
        self.lbl_score_status: Gtk.Label = g("lbl_score_status")
        self.lbl_score_detail: Gtk.Label = g("lbl_score_detail")
        self.lbl_dash_cpu_title: Gtk.Label = g("lbl_dash_cpu_title")
        self.lbl_dash_ram_title: Gtk.Label = g("lbl_dash_ram_title")
        self.lbl_dash_disk_title: Gtk.Label = g("lbl_dash_disk_title")
        self.lbl_dash_cpu_val: Gtk.Label = g("lbl_dash_cpu_val")
        self.lbl_dash_ram_val: Gtk.Label = g("lbl_dash_ram_val")
        self.lbl_dash_disk_val: Gtk.Label = g("lbl_dash_disk_val")
        self.level_dash_cpu: Gtk.LevelBar = g("level_dash_cpu")
        self.level_dash_ram: Gtk.LevelBar = g("level_dash_ram")
        self.level_dash_disk: Gtk.LevelBar = g("level_dash_disk")
        self.lbl_quick_actions_title: Gtk.Label = g("lbl_quick_actions_title")
        self.lbl_dash_scan_title: Gtk.Label = g("lbl_dash_scan_title")
        self.lbl_dash_scan_desc: Gtk.Label = g("lbl_dash_scan_desc")
        self.lbl_dash_health_title: Gtk.Label = g("lbl_dash_health_title")
        self.lbl_dash_health_desc: Gtk.Label = g("lbl_dash_health_desc")
        self.lbl_dash_insights_title: Gtk.Label = g("lbl_dash_insights_title")
        self.lbl_dash_insights_desc: Gtk.Label = g("lbl_dash_insights_desc")
        self.lbl_sysstate_title: Gtk.Label = g("lbl_sysstate_title")
        self.lbl_systemd_state: Gtk.Label = g("lbl_systemd_state")
        self.lbl_failed_count: Gtk.Label = g("lbl_failed_count")
        self.lbl_errors_24h: Gtk.Label = g("lbl_errors_24h")
        self.lbl_dash_last_maintenance: Gtk.Label = g("lbl_dash_last_maintenance")

        # ── Cleaner ──
        self.file_list_store: Gtk.ListStore = g("file_list_store")
        self.info_label: Gtk.Label = g("info_label")
        self.info_bar: Gtk.InfoBar = g("info_bar")
        self.summary_label: Gtk.Label = g("summary_label")
        self.btn_scan: Gtk.Button = g("btn_scan")
        self.btn_clean: Gtk.Button = g("btn_clean")

        # ── Health monitor ──
        self.lbl_health_page_title: Gtk.Label = g("lbl_health_page_title")
        self.lbl_health_score_big: Gtk.Label = g("lbl_health_score_big")
        self.lbl_health_status_text: Gtk.Label = g("lbl_health_status_text")
        self.lbl_health_cpu_label: Gtk.Label = g("lbl_health_cpu_label")
        self.lbl_health_ram_label: Gtk.Label = g("lbl_health_ram_label")
        self.lbl_health_disk_label: Gtk.Label = g("lbl_health_disk_label")
        self.lbl_health_cpu_val: Gtk.Label = g("lbl_health_cpu_val")
        self.lbl_health_ram_val: Gtk.Label = g("lbl_health_ram_val")
        self.lbl_health_disk_val: Gtk.Label = g("lbl_health_disk_val")
        self.level_health_cpu: Gtk.LevelBar = g("level_health_cpu")
        self.level_health_ram: Gtk.LevelBar = g("level_health_ram")
        self.level_health_disk: Gtk.LevelBar = g("level_health_disk")

        # ── Insights ──
        self.lbl_insights_title: Gtk.Label = g("lbl_insights_title")
        self.btn_refresh_insights: Gtk.Button = g("btn_refresh_insights")
        self.box_insights_container: Gtk.Box = g("box_insights_container")
        self.box_insights_placeholder: Gtk.Box = g("box_insights_placeholder")

        # ── History ──
        self.lbl_history_title: Gtk.Label = g("lbl_history_title")
        self.history_list_store: Gtk.ListStore = g("history_list_store")

        # ── Treeview columns ──
        self.col_toggle: Gtk.TreeViewColumn = g("col_toggle")
        self.col_category: Gtk.TreeViewColumn = g("col_category")
        self.col_description: Gtk.TreeViewColumn = g("col_description")
        self.col_size: Gtk.TreeViewColumn = g("col_size")
        self.hist_col_date: Gtk.TreeViewColumn = g("hist_col_date")
        self.hist_col_category: Gtk.TreeViewColumn = g("hist_col_category")
        self.hist_col_freed: Gtk.TreeViewColumn = g("hist_col_freed")
        self.hist_col_status: Gtk.TreeViewColumn = g("hist_col_status")

        # ── Settings ──
        self.lbl_settings_title: Gtk.Label = g("lbl_settings_title")
        self.lbl_settings_language: Gtk.Label = g("lbl_settings_language")
        self.lbl_language_select: Gtk.Label = g("lbl_language_select")
        self.combo_language: Gtk.ComboBoxText = g("combo_language")
        self.lbl_auto_maintenance_title: Gtk.Label = g("lbl_auto_maintenance_title")
        self.lbl_auto_maintenance_desc: Gtk.Label = g("lbl_auto_maintenance_desc")
        self.switch_auto_maintenance: Gtk.Switch = g("switch_auto_maintenance")
        self.box_auto_settings: Gtk.Box = g("box_auto_settings")
        self.lbl_scheduling_title: Gtk.Label = g("lbl_scheduling_title")
        self.lbl_frequency_title: Gtk.Label = g("lbl_frequency_title")
        self.combo_frequency: Gtk.ComboBoxText = g("combo_frequency")
        self.lbl_conditions_title: Gtk.Label = g("lbl_conditions_title")
        self.lbl_idle_title: Gtk.Label = g("lbl_idle_title")
        self.spin_idle: Gtk.SpinButton = g("spin_idle")
        self.lbl_minutes_suffix: Gtk.Label = g("lbl_minutes_suffix")
        self.lbl_ac_power_title: Gtk.Label = g("lbl_ac_power_title")
        self.switch_ac_power: Gtk.Switch = g("switch_ac_power")
        self.lbl_notifications_title: Gtk.Label = g("lbl_notifications_title")
        self.lbl_notify_done_title: Gtk.Label = g("lbl_notify_done_title")
        self.switch_notify: Gtk.Switch = g("switch_notify")
        
        self.lbl_ai_config_title: Gtk.Label = g("lbl_ai_config_title")
        self.lbl_ai_provider: Gtk.Label = g("lbl_ai_provider")
        self.combo_ai_provider: Gtk.ComboBoxText = g("combo_ai_provider")
        self.lbl_ai_api_key: Gtk.Label = g("lbl_ai_api_key")
        self.entry_ai_api_key: Gtk.Entry = g("entry_ai_api_key")
        self.lbl_ai_model: Gtk.Label = g("lbl_ai_model")
        self.entry_ai_model: Gtk.Entry = g("entry_ai_model")

        self.expander_advanced: Gtk.Expander = g("expander_advanced")
        self.lbl_disk_threshold_title: Gtk.Label = g("lbl_disk_threshold_title")
        self.switch_disk_threshold: Gtk.Switch = g("switch_disk_threshold")
        self.spin_disk_percent: Gtk.SpinButton = g("spin_disk_percent")
        self.lbl_last_maintenance_title: Gtk.Label = g("lbl_last_maintenance_title")
        self.lbl_last_maintenance: Gtk.Label = g("lbl_last_maintenance")

        # ── Dialogs ──
        self.about_dialog: Gtk.AboutDialog = g("about_dialog")
        self.clean_confirm_dialog: Gtk.MessageDialog = g("clean_confirm_dialog")

    # ── Translation ──────────────────────────────────────────────────────────
    def _apply_translations(self) -> None:
        """Replace all hardcoded English labels with the active locale strings."""
        # Header bar
        self.builder.get_object("header_bar").set_subtitle(_("app_subtitle"))

        # ── Dashboard page ──
        self.lbl_welcome.set_text(_("lbl_welcome"))
        self.lbl_welcome_sub.set_text(_("lbl_welcome_sub"))
        self.lbl_score_status.set_text(_("lbl_calculating"))
        self.lbl_score_detail.set_text(_("lbl_monitoring"))
        self.lbl_dash_cpu_title.set_text(_("lbl_cpu"))
        self.lbl_dash_ram_title.set_text(_("lbl_memory"))
        self.lbl_dash_disk_title.set_text(_("lbl_disk"))
        self.lbl_quick_actions_title.set_text(_("lbl_quick_actions"))
        self.lbl_dash_scan_title.set_text(_("dash_scan_title"))
        self.lbl_dash_scan_desc.set_text(_("dash_scan_desc"))
        self.lbl_dash_health_title.set_text(_("dash_health_title"))
        self.lbl_dash_health_desc.set_text(_("dash_health_desc"))
        self.lbl_dash_insights_title.set_text(_("dash_insights_title"))
        self.lbl_dash_insights_desc.set_text(_("dash_insights_desc"))
        self.lbl_sysstate_title.set_text(_("lbl_system_state"))

        # Stack page titles (sidebar labels)
        self.content_stack.child_set_property(
            self.content_stack.get_child_by_name("page_dashboard"), "title", _("page_dashboard"))
        self.content_stack.child_set_property(
            self.content_stack.get_child_by_name("page_cleaner"), "title", _("page_cleaner"))
        self.content_stack.child_set_property(
            self.content_stack.get_child_by_name("page_health"), "title", _("page_health"))
        self.content_stack.child_set_property(
            self.content_stack.get_child_by_name("page_insights"), "title", _("page_insights"))
        self.content_stack.child_set_property(
            self.content_stack.get_child_by_name("page_history"), "title", _("page_history"))
        self.content_stack.child_set_property(
            self.content_stack.get_child_by_name("page_settings"), "title", _("page_settings"))

        # ── Cleaner page ──
        self.info_label.set_text(_("msg_ready"))
        self.btn_scan.set_label(_("btn_scan"))
        self.btn_clean.set_label(_("btn_clean"))
        self.col_toggle.set_title(_("col_select"))
        self.col_category.set_title(_("col_category"))
        self.col_description.set_title(_("col_description"))
        self.col_size.set_title(_("col_size"))

        # ── Health page ──
        self.lbl_health_page_title.set_text(_("lbl_health_title"))
        self.lbl_health_status_text.set_text(_("lbl_health_score"))
        self.lbl_health_cpu_label.set_text(_("lbl_cpu_usage"))
        self.lbl_health_ram_label.set_text(_("lbl_memory_usage"))
        self.lbl_health_disk_label.set_text(_("lbl_disk_usage"))

        # ── Insights page ──
        self.lbl_insights_title.set_text(_("insights_title"))
        self.btn_refresh_insights.set_label(_("btn_analyze"))

        # ── History page ──
        self.lbl_history_title.set_text(_("history_title"))
        self.hist_col_date.set_title(_("col_date"))
        self.hist_col_category.set_title(_("col_categories"))
        self.hist_col_freed.set_title(_("col_freed"))
        self.hist_col_status.set_title(_("col_status"))

        # ── Settings page ──
        self.lbl_settings_title.set_text(_("settings_title"))
        self.lbl_settings_language.set_text(_("settings_language"))
        self.lbl_language_select.set_text(_("language_selection"))
        self.lbl_auto_maintenance_title.set_text(_("settings_auto_maintenance"))
        self.lbl_auto_maintenance_desc.set_text(_("settings_auto_desc"))
        self.lbl_scheduling_title.set_text(_("settings_scheduling"))
        self.lbl_frequency_title.set_text(_("settings_frequency"))
        self.lbl_conditions_title.set_text(_("settings_conditions"))
        self.lbl_idle_title.set_text(_("settings_idle"))
        self.lbl_minutes_suffix.set_text(_("minutes_suffix"))
        self.lbl_ac_power_title.set_text(_("settings_ac_power"))
        self.lbl_notifications_title.set_text(_("settings_notifications"))
        self.lbl_notify_done_title.set_text(_("settings_notify_done"))
        self.expander_advanced.set_label(_("settings_advanced"))
        self.lbl_disk_threshold_title.set_text(_("settings_disk_threshold"))
        self.lbl_last_maintenance_title.set_text(_("settings_last_maintenance"))

        # ── Confirm dialog ──
        self.clean_confirm_dialog.set_property("text", _("confirm_title"))
        
        # ── AI Config ──
        self.lbl_ai_config_title.set_text(_("settings_ai_title"))
        self.lbl_ai_provider.set_text(_("settings_ai_provider"))
        self.lbl_ai_api_key.set_text(_("settings_ai_api_key"))
        self.lbl_ai_model.set_text(_("settings_ai_model"))

    # ── CSS ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_css() -> None:
        """Inject minimal runtime CSS (theme-respecting, no hardcoded colours)."""
        css = b"""
            .card-button {
                border-radius: 8px;
                padding: 8px;
            }
            .card-button:hover {
                background-color: alpha(@theme_fg_color, 0.08);
            }
            .card {
                background-color: alpha(@theme_fg_color, 0.05);
                border-radius: 8px;
                padding: 8px;
            }
            .dim-label {
                opacity: 0.6;
            }
            .error {
                color: @error_color;
            }
            .warning {
                color: @warning_color;
            }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ── Application icon ────────────────────────────────────────────────────
    def _set_app_icon(self) -> None:
        try:
            icon_theme = Gtk.IconTheme.get_default()
            if icon_theme.has_icon("io.github.gkdevelopers.GKHealter"):
                self.window.set_icon_name("io.github.gkdevelopers.GKHealter")
            else:
                icon_path = os.path.join(
                    os.path.dirname(__file__), "..", "icons",
                    "hicolor", "128x128", "apps",
                    "io.github.gkdevelopers.GKHealter.png",
                )
                if os.path.exists(icon_path):
                    self.window.set_icon_from_file(icon_path)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  SIGNAL HANDLERS  (names must match handler="" in XML)
    # ══════════════════════════════════════════════════════════════════════════

    # ── Header bar ───────────────────────────────────────────────────────────
    def on_about_clicked(self, _btn: Gtk.Button) -> None:
        self.about_dialog.run()
        self.about_dialog.hide()

    def on_header_refresh_clicked(self, _btn: Gtk.Button) -> None:
        self._refresh_dashboard()

    # ── Dashboard quick-action cards ─────────────────────────────────────────
    def on_dash_scan_clicked(self, _btn: Gtk.Button) -> None:
        self.content_stack.set_visible_child_name("page_cleaner")
        self.on_scan_clicked(None)

    def on_dash_health_clicked(self, _btn: Gtk.Button) -> None:
        self.content_stack.set_visible_child_name("page_health")

    def on_dash_insights_clicked(self, _btn: Gtk.Button) -> None:
        self.content_stack.set_visible_child_name("page_insights")
        self.on_refresh_insights_clicked(None)

    # ── Window ───────────────────────────────────────────────────────────────
    def on_window_destroy(self, _win: Gtk.Window) -> None:
        self.health_engine.stop_monitoring()
        if self._health_timer_id:
            GLib.source_remove(self._health_timer_id)
        Gtk.main_quit()

    # ── Cleaner page ─────────────────────────────────────────────────────────
    def on_scan_clicked(self, _btn: Optional[Gtk.Button]) -> None:
        if self.is_cleaning_in_progress:
            return
        self.file_list_store.clear()
        self.btn_clean.set_sensitive(False)
        self._set_info(_("msg_scanning"), "info")
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def on_clean_clicked(self, _btn: Gtk.Button) -> None:
        if self.is_cleaning_in_progress or not self.scan_data:
            return

        # Collect selected items
        selected = self._get_selected_items()
        if not selected:
            self._set_info(_("msg_nothing_selected"), "warning")
            return

        # Build confirmation message
        total_bytes = sum(item['size_bytes'] for item in selected)
        has_system = any(item['system'] for item in selected)
        msg = _("msg_confirm_clean").replace("{size}", format_size(total_bytes))
        if has_system:
            msg += "\n\n" + _("msg_system_auth_warning")

        self.clean_confirm_dialog.format_secondary_text(msg)
        response = self.clean_confirm_dialog.run()
        self.clean_confirm_dialog.hide()

        if response == Gtk.ResponseType.OK:
            self.is_cleaning_in_progress = True
            self.btn_scan.set_sensitive(False)
            self.btn_clean.set_sensitive(False)
            self._set_info(_("msg_cleaning"), "info")
            threading.Thread(
                target=self._clean_thread, args=(selected,), daemon=True
            ).start()

    def on_cell_toggled(self, renderer: Gtk.CellRendererToggle, path: str) -> None:
        self.file_list_store[path][0] = not self.file_list_store[path][0]
        self._update_summary()

    # ── Insights page ────────────────────────────────────────────────────────
    def on_refresh_insights_clicked(self, _btn: Optional[Gtk.Button] = None) -> None:
        # Hide previous results
        for child in self.box_insights_container.get_children():
            # If the placeholder is one of the children, we can choose to hide or remove it.
            # But we added it in XML. Ideally we shouldn't remove XML-defined widgets if we want to reuse them.
            # However, simpler approach: Remove generated widgets, show placeholder if empty.
            if child == self.box_insights_placeholder:
                child.set_visible(False)
            else:
                self.box_insights_container.remove(child)

        lbl = Gtk.Label(label=_("msg_analyzing"))
        lbl.set_visible(True)
        lbl.get_style_context().add_class("dim-label")
        self.box_insights_container.add(lbl)

        threading.Thread(target=self._run_analysis, daemon=True).start()

    # ── Settings page ────────────────────────────────────────────────────────
    def on_language_changed(self, combo: Gtk.ComboBoxText) -> None:
        lang_id = combo.get_active_id()
        if lang_id:
            self.settings_manager.set("language", lang_id)
            I18nManager().load_language(lang_id)
            self._apply_translations()
            self._update_frequency_labels()

    def on_auto_maintenance_toggled(self, switch: Gtk.Switch, _pspec) -> None:
        active = switch.get_active()
        self.settings_manager.set("auto_maintenance_enabled", active)
        self.box_auto_settings.set_visible(active)

    def on_frequency_changed(self, combo: Gtk.ComboBoxText) -> None:
        freq_id = combo.get_active_id()
        if freq_id:
            self.settings_manager.set("maintenance_frequency_days", int(freq_id))

    def on_idle_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings_manager.set(
            "idle_threshold_minutes", int(spin.get_value())
        )

    def on_ac_power_toggled(self, switch: Gtk.Switch, _pspec) -> None:
        self.settings_manager.set("check_ac_power", switch.get_active())

    def on_notify_toggled(self, switch: Gtk.Switch, _pspec) -> None:
        self.settings_manager.set("notify_on_completion", switch.get_active())

    def on_disk_threshold_toggled(self, switch: Gtk.Switch, _pspec) -> None:
        self.settings_manager.set("disk_threshold_enabled", switch.get_active())

    def on_disk_percent_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings_manager.set(
            "disk_threshold_percent", int(spin.get_value())
        )

    def on_ai_provider_changed(self, combo: Gtk.ComboBoxText) -> None:
        val = combo.get_active_id()
        if not val:
            return
            
        self.settings_manager.set("ai_provider", val)
            
        # Optional: Auto-switch model default if it looks like the other provider's model
        current_model = self.settings_manager.get("ai_model") or ""
        new_model = current_model

        if val == "openai":
            if "gpt" not in current_model:
                new_model = "gpt-3.5-turbo"
        elif val == "gemini":
            if "gemini" not in current_model:
                new_model = "gemini-1.5-flash"
        
        if new_model != current_model:
            self.settings_manager.set("ai_model", new_model)
            self.entry_ai_model.set_text(new_model)

        self._update_ai_config()

    def on_ai_key_changed(self, entry: Gtk.Entry) -> None:
        val = entry.get_text()
        self.settings_manager.set("ai_api_key", val)
        self._update_ai_config()

    def on_ai_model_changed(self, entry: Gtk.Entry) -> None:
        val = entry.get_text()
        self.settings_manager.set("ai_model", val)
        self._update_ai_config()
    
    def _update_ai_config(self) -> None:
        sm = self.settings_manager
        self.ai_engine.configure(
            sm.get("ai_provider"), sm.get("ai_api_key"), sm.get("ai_model")
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    # ── Settings initialisation ──────────────────────────────────────────────
    def _init_settings_ui(self) -> None:
        """Populate combo-boxes and restore saved values into the Settings page."""
        sm = self.settings_manager

        # Language combo (these stay untranslated – they are language names)
        self.combo_language.append("auto", "Auto")
        self.combo_language.append("en", "English")
        self.combo_language.append("tr", "Türkçe")
        current_lang = sm.get("language") or "auto"
        self.combo_language.set_active_id(current_lang)

        # Frequency combo
        self._populate_frequency_combo()
        freq = str(sm.get("maintenance_frequency_days"))
        self.combo_frequency.set_active_id(freq)

        # AI Settings
        self.combo_ai_provider.append("gemini", "Gemini (Google)")
        self.combo_ai_provider.append("openai", "ChatGPT (OpenAI)")
        ai_prov = sm.get("ai_provider") or "gemini"
        self.combo_ai_provider.set_active_id(ai_prov)

        self.entry_ai_api_key.set_text(sm.get("ai_api_key") or "")
        self.entry_ai_model.set_text(sm.get("ai_model") or "gpt-3.5-turbo")

        # Configure initial AI engine state
        self.ai_engine.configure(ai_prov, sm.get("ai_api_key"), sm.get("ai_model"))

        # Restore switch / spin values (block signals temporarily)
        self.switch_auto_maintenance.set_active(sm.get("auto_maintenance_enabled"))
        self.box_auto_settings.set_visible(sm.get("auto_maintenance_enabled"))

        self.spin_idle.set_value(sm.get("idle_threshold_minutes"))
        self.switch_ac_power.set_active(sm.get("check_ac_power"))
        self.switch_notify.set_active(sm.get("notify_on_completion"))
        self.switch_disk_threshold.set_active(sm.get("disk_threshold_enabled"))
        self.spin_disk_percent.set_value(sm.get("disk_threshold_percent"))

        # Last maintenance label
        last = sm.get("last_maintenance_date")
        self.lbl_last_maintenance.set_text(last if last else _("lbl_never"))

    def _populate_frequency_combo(self) -> None:
        """Fill the frequency combo with translated labels."""
        self.combo_frequency.remove_all()
        self.combo_frequency.append("1", _("freq_daily"))
        self.combo_frequency.append("7", _("freq_weekly"))
        self.combo_frequency.append("14", _("freq_biweekly"))
        self.combo_frequency.append("30", _("freq_monthly"))

    def _update_frequency_labels(self) -> None:
        """Re-populate frequency combo after a language change."""
        active = self.combo_frequency.get_active_id()
        self._populate_frequency_combo()
        if active:
            self.combo_frequency.set_active_id(active)

    # ── Health timer (periodic UI refresh) ───────────────────────────────────
    def _start_health_timer(self) -> None:
        """Tick every 2 seconds to update dashboard / health page metrics."""
        self._health_timer_id = GLib.timeout_add_seconds(2, self._on_health_tick)

    def _on_health_tick(self) -> bool:
        metrics = self.health_engine.get_metrics()
        status = self.health_engine.get_detailed_status()

        cpu = metrics['cpu']
        ram = metrics['ram']
        disk = metrics['disk']
        score = metrics['score']

        # Dashboard meters
        self.lbl_dash_cpu_val.set_text(f"{cpu:.0f}%")
        self.lbl_dash_ram_val.set_text(f"{ram:.0f}%")
        self.lbl_dash_disk_val.set_text(f"{disk:.0f}%")
        self.level_dash_cpu.set_value(cpu)
        self.level_dash_ram.set_value(ram)
        self.level_dash_disk.set_value(disk)

        # Dashboard score card
        self.lbl_score_value.set_text(str(int(score)))
        self.lbl_score_status.set_text(status)
        self._set_score_detail(score)

        # Health page (mirrors dashboard but bigger)
        self.lbl_health_score_big.set_text(str(int(score)))
        self.lbl_health_status_text.set_text(f"{_('health_score_label')} — {status}")
        self.lbl_health_cpu_val.set_text(f"{cpu:.0f}%")
        self.lbl_health_ram_val.set_text(f"{ram:.0f}%")
        self.lbl_health_disk_val.set_text(f"{disk:.0f}%")
        self.level_health_cpu.set_value(cpu)
        self.level_health_ram.set_value(ram)
        self.level_health_disk.set_value(disk)

        return True  # keep the timer alive

    def _set_score_detail(self, score: float) -> None:
        if score >= 90:
            self.lbl_score_detail.set_text(_("score_detail_excellent"))
        elif score >= 70:
            self.lbl_score_detail.set_text(_("score_detail_good"))
        elif score >= 50:
            self.lbl_score_detail.set_text(_("score_detail_fair"))
        else:
            self.lbl_score_detail.set_text(_("score_detail_critical"))

    # ── Dashboard refresh (system state section) ─────────────────────────────
    def _refresh_dashboard(self) -> None:
        """Fetch system-state info in a background thread."""
        threading.Thread(target=self._fetch_dashboard_state, daemon=True).start()

    def _fetch_dashboard_state(self) -> None:
        state = self.service_analyzer.get_system_state()
        failed = self.service_analyzer.get_failed_services()
        errors = self.log_analyzer.get_error_count_24h()
        last = self.settings_manager.get("last_maintenance_date") or _("lbl_never")

        GLib.idle_add(self._apply_dashboard_state, state, failed, errors, last)

    def _apply_dashboard_state(
        self, state: str, failed: list, errors: int, last: str
    ) -> None:
        self.lbl_systemd_state.set_text(state)
        self.lbl_failed_count.set_text(str(len(failed)))
        self.lbl_errors_24h.set_text(str(errors))
        self.lbl_dash_last_maintenance.set_text(last)

    # ── Scan thread ──────────────────────────────────────────────────────────
    def _scan_thread(self) -> None:
        results = self.cleaner.scan()
        GLib.idle_add(self._on_scan_done, results)

    def _on_scan_done(self, results: List[Dict[str, Any]]) -> None:
        self.scan_data = results
        self.file_list_store.clear()

        if not results:
            self._set_info(_("msg_no_items"), "info")
            return

        for item in results:
            self.file_list_store.append([
                True,                    # toggle
                item['category'],        # category
                item['desc'],            # description
                item['size_str'],        # size string
                item['size_bytes'],      # size bytes (hidden)
                item['path'],            # path (hidden)
                item['system'],          # is_system (hidden)
            ])

        count = len(results)
        self._set_info(
            _("msg_scan_complete").replace("{count}", str(count)), "info"
        )
        self.btn_clean.set_sensitive(True)
        self._update_summary()

    # ── Clean thread ─────────────────────────────────────────────────────────
    def _clean_thread(self, selected: List[Dict[str, Any]]) -> None:
        success, fail, errors = self.cleaner.clean(selected)
        categories = [item['category'] for item in selected]
        total_bytes = sum(item['size_bytes'] for item in selected)
        GLib.idle_add(
            self._on_clean_done, success, fail, errors, categories, total_bytes
        )

    def _on_clean_done(
        self,
        success: int,
        fail: int,
        errors: List[str],
        categories: List[str],
        total_bytes: int,
    ) -> None:
        self.is_cleaning_in_progress = False
        self.btn_scan.set_sensitive(True)

        total_str = format_size(total_bytes)
        if fail == 0:
            status = _("status_success")
            self._set_info(
                _("msg_clean_success").replace("{size}", total_str), "info"
            )
        elif success > 0:
            status = _("status_partial")
            self._set_info(
                _("msg_clean_partial").replace("{ok}", str(success)).replace(
                    "{fail}", str(fail)
                ),
                "warning",
            )
        else:
            status = _("status_failed")
            self._set_info(_("msg_clean_failed"), "error")

        self.history_manager.add_entry(categories, total_str, status)
        self._load_history_into_view()

        # Update last-maintenance timestamp
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.settings_manager.set("last_maintenance_date", now)
        self.lbl_last_maintenance.set_text(now)
        self.lbl_dash_last_maintenance.set_text(now)

        self.file_list_store.clear()
        self.scan_data = []
        self.btn_clean.set_sensitive(False)
        self.summary_label.set_text("Total: 0 MB")

    # ── Analysis thread (Insights page) ──────────────────────────────────────
    def _run_analysis(self) -> None:
        failed_services = self.service_analyzer.get_failed_services()
        slow_services = self.service_analyzer.get_slow_startup_services()
        errors_24h = self.log_analyzer.get_error_count_24h()
        large_files = self.disk_analyzer.get_large_files(
            os.path.expanduser("~"), limit=5
        )
        metrics = self.health_engine.get_metrics()

        recs = self.recommendation_engine.analyze_health(metrics)
        recs += self.recommendation_engine.analyze_services(
            failed_services, slow_services
        )
        recs += self.recommendation_engine.analyze_logs(errors_24h)

        ai_insight = self.ai_engine.generate_insight(
            metrics, failed_services, errors_24h
        )

        GLib.idle_add(
            self._display_insights, recs, ai_insight, large_files,
            failed_services, slow_services, errors_24h
        )

    def _display_insights(
        self,
        recs: list,
        ai_insight: str,
        large_files: list,
        failed_services: list,
        slow_services: list,
        errors_24h: int,
    ) -> None:
        # Clear container
        for child in self.box_insights_container.get_children():
            if child == self.box_insights_placeholder:
                child.set_visible(False)
            else:
                self.box_insights_container.remove(child)

        has_content = False

        # Recommendations
        if recs:
            has_content = True
            self._add_section_header(_("insights_recommendations"))
            for r in recs:
                level = r['type'] # warning or error
                icon = "dialog-warning-symbolic" if level == 'warning' else "dialog-error-symbolic"
                self._add_insight_card(r['message'], icon, level)

        # Failed services
        if failed_services:
            has_content = True
            self._add_section_header(f"{_('insights_failed_services')} ({len(failed_services)})")
            for svc in failed_services:
                self._add_insight_card(svc, "service-template-symbolic", "error")

        # Slow boot services
        if slow_services:
            has_content = True
            self._add_section_header(_("insights_slow_boot"))
            for s in slow_services:
                 # TODO: Add specific icon or level if needed
                self._add_insight_card(f"{s['service']} ({s['time']})", "speedometer-symbolic", "warning")

        # Errors
        if errors_24h > 0:
            has_content = True
            self._add_section_header(f"{_('insights_journal_errors')}: {errors_24h}")
            self._add_insight_card(f"Journal has {errors_24h} errors in last 24h", "dialog-error-symbolic", "error")

        # Large files
        if large_files:
            has_content = True
            self._add_section_header(_("insights_large_files"))
            for f in large_files:
                self._add_insight_card(f"{f['size']} - {f['path']}", "folder-symbolic")

        # AI Insight
        if ai_insight and "disabled" not in ai_insight:
            has_content = True
            self._add_section_header(_("insights_ai"))
            
            # Use a card or a well-styled label for AI text
            # Since AI text is long, use a TextView or Label with wrapping inside a card
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card.set_visible(True)
            card.get_style_context().add_class("card")
            card.set_margin_bottom(12)
            card.set_margin_top(4)
            card.set_margin_start(4)
            card.set_margin_end(4)
            
            lbl = Gtk.Label(label=ai_insight)
            lbl.set_visible(True)
            lbl.set_line_wrap(True)
            lbl.set_xalign(0)
            lbl.set_selectable(True)
            card.add(lbl)
            self.box_insights_container.add(card)

        if not has_content:
            # Show "All Good" message
            lbl = Gtk.Label(label=_("msg_no_items"))
            lbl.set_visible(True)
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.get_style_context().add_class("dim-label")
            self.box_insights_container.add(lbl)
        
        self.box_insights_container.show_all()

    def _add_section_header(self, title: str) -> None:
        lbl = Gtk.Label(label=title)
        lbl.set_visible(True)
        lbl.set_xalign(0)
        lbl.get_style_context().add_class("dim-label")
        lbl.set_margin_top(12)
        lbl.set_margin_bottom(4)
        attributes = Pango.AttrList()
        attributes.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        lbl.set_attributes(attributes)
        self.box_insights_container.add(lbl)

    def _add_insight_card(self, message: str, icon_name: str, level: str = "info") -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_visible(True)
        box.get_style_context().add_class("card") # Requires CSS for .card
        box.set_margin_bottom(6)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_border_width(8)
        
        # Icon
        try:
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND) # Larger icon
        except:
             img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

        img.set_visible(True)
        if level == "error":
            img.get_style_context().add_class("error")
        elif level == "warning":
            img.get_style_context().add_class("warning")
        
        # Icon alignment
        img.set_valign(Gtk.Align.START)
        box.pack_start(img, False, False, 0)
        
        # Label
        lbl = Gtk.Label(label=message)
        lbl.set_visible(True)
        lbl.set_xalign(0)
        lbl.set_line_wrap(True)
        box.pack_start(lbl, True, True, 0)
        
        self.box_insights_container.add(box)


    # ── History ──────────────────────────────────────────────────────────────
    def _load_history_into_view(self) -> None:
        self.history_list_store.clear()
        for entry in self.history_manager.get_all_entries():
            self.history_list_store.append([
                entry.get("date", ""),
                entry.get("categories", ""),
                entry.get("total_freed", ""),
                entry.get("status", ""),
            ])

    # ── Cleaner helpers ──────────────────────────────────────────────────────
    def _get_selected_items(self) -> List[Dict[str, Any]]:
        selected: List[Dict[str, Any]] = []
        for row in self.file_list_store:
            if row[0]:  # toggle column
                selected.append({
                    'category': row[1],
                    'path': row[5],
                    'size_bytes': row[4],
                    'system': row[6],
                })
        return selected

    def _update_summary(self) -> None:
        total = sum(row[4] for row in self.file_list_store if row[0])
        self.summary_label.set_text(
            _("summary_total").replace("{size}", format_size(total))
        )

    def _set_info(self, message: str, level: str = "info") -> None:
        """Update the info-bar label and message type."""
        type_map = {
            "info": Gtk.MessageType.INFO,
            "warning": Gtk.MessageType.WARNING,
            "error": Gtk.MessageType.ERROR,
        }
        self.info_bar.set_message_type(type_map.get(level, Gtk.MessageType.INFO))
        self.info_label.set_text(message)
