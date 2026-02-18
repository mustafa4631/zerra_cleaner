"""
GK Healter – Main UI Module
All layout is defined in resources/main_window.ui (GTK Builder XML).
This module handles signal connections, business logic, and dynamic content only.
"""

import os
import threading
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gk-healter.ui")

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
from src.pardus_analyzer import PardusAnalyzer
from src.security_scanner import SecurityScanner
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
        self.pardus_analyzer = PardusAnalyzer()
        self.security_scanner = SecurityScanner()

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

        # Detect Pardus and show badge if applicable
        self._is_pardus: bool = False
        self._pardus_version: str = ""
        threading.Thread(target=self._detect_pardus_async, daemon=True).start()

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
        self.combo_ai_model: Gtk.ComboBoxText = g("combo_ai_model")
        # Connect to internal entry for custom model names
        entry = self.combo_ai_model.get_child()
        if isinstance(entry, Gtk.Entry):
            entry.connect("changed", self.on_ai_model_entry_changed)

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
        """Inject runtime CSS for a polished, professional appearance."""
        css = """
            /* -- Global polish ------------------------------------------------- */
            .view, .sidebar {
                /* ensure clean background */
            }

            /* -- Card containers ----------------------------------------------- */
            .card {
                background-color: alpha(@theme_fg_color, 0.04);
                border: 1px solid alpha(@theme_fg_color, 0.08);
                border-radius: 12px;
                padding: 10px;
            }

            .card-elevated {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid alpha(@theme_fg_color, 0.10);
                border-radius: 14px;
                padding: 16px;
            }

            .card-button {
                border-radius: 12px;
                padding: 8px;
                border: 1px solid alpha(@theme_fg_color, 0.06);
                background-color: alpha(@theme_fg_color, 0.02);
                transition: background-color 200ms ease;
            }
            .card-button:hover {
                background-color: alpha(@theme_fg_color, 0.10);
                border-color: alpha(@theme_fg_color, 0.15);
            }

            /* -- Action buttons ------------------------------------------------ */
            .suggested-action {
                background: linear-gradient(
                    to bottom,
                    shade(@theme_selected_bg_color, 1.08),
                    @theme_selected_bg_color
                );
                color: @theme_selected_fg_color;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 8px;
                border: none;
            }
            .suggested-action:hover {
                background: shade(@theme_selected_bg_color, 1.15);
            }

            /* -- Section headers ---------------------------------------------- */
            .section-header {
                font-weight: bold;
                opacity: 0.7;
                padding: 4px 0px;
            }

            /* -- Score badge colours ------------------------------------------- */
            .score-excellent { color: #2e7d32; }
            .score-good      { color: #558b2f; }
            .score-fair       { color: #f57f17; }
            .score-critical   { color: #c62828; }

            /* -- Resource meter severity --------------------------------------- */
            .meter-normal  levelbar trough block.filled { background-color: #4caf50; }
            .meter-warning levelbar trough block.filled { background-color: #ff9800; }
            .meter-danger  levelbar trough block.filled { background-color: #f44336; }

            .resource-label-normal   { color: #4caf50; font-weight: bold; }
            .resource-label-warning  { color: #ff9800; font-weight: bold; }
            .resource-label-danger   { color: #f44336; font-weight: bold; }

            /* -- Pardus badge -------------------------------------------------- */
            .pardus-badge {
                background: linear-gradient(135deg, #1a5276, #2e86c1);
                color: white;
                border-radius: 10px;
                padding: 14px 20px;
                font-weight: bold;
            }
            .pardus-badge-label {
                color: white;
                font-weight: bold;
            }
            .pardus-badge-sub {
                color: alpha(white, 0.85);
            }

            /* -- Resource card ------------------------------------------------- */
            .resource-card {
                background-color: alpha(@theme_fg_color, 0.03);
                border: 1px solid alpha(@theme_fg_color, 0.08);
                border-radius: 12px;
                padding: 16px;
            }

            /* -- Misc ---------------------------------------------------------- */
            .dim-label {
                opacity: 0.55;
            }
            .error {
                color: @error_color;
            }
            .warning {
                color: @warning_color;
            }
            .mono-label {
                font-family: monospace;
            }
            .score-big {
                font-size: 48px;
                font-weight: 800;
            }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
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
                # Try loading SVG first (scalable), then fallback to PNG
                icon_path_svg = os.path.join(
                    os.path.dirname(__file__), "..", "icons",
                    "hicolor", "scalable", "apps",
                    "io.github.gkdevelopers.GKHealter.svg",
                )
                if os.path.exists(icon_path_svg):
                    self.window.set_icon_from_file(icon_path_svg)
                else:
                    icon_path_png = os.path.join(
                        os.path.dirname(__file__), "..", "icons",
                        "hicolor", "128x128", "apps",
                        "io.github.gkdevelopers.GKHealter.png",
                    )
                    if os.path.exists(icon_path_png):
                        self.window.set_icon_from_file(icon_path_png)
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
        self._populate_ai_models(val)

        # Auto-switch model default if needed
        current_model = self.settings_manager.get("ai_model") or ""
        new_model = current_model

        if val == "openai":
            if "gpt" not in current_model:
                new_model = "gpt-4o"
        elif val == "gemini":
            if "gemini" not in current_model:
                new_model = "gemini-2.5-flash"

        if new_model != current_model:
            self.settings_manager.set("ai_model", new_model)
            # Update the entry inside the combo
            entry = self.combo_ai_model.get_child()
            if isinstance(entry, Gtk.Entry):
                entry.set_text(new_model)

        self._update_ai_config()

    def on_ai_key_changed(self, entry: Gtk.Entry) -> None:
        val = entry.get_text()
        self.settings_manager.set("ai_api_key", val)
        self._update_ai_config()

    def on_ai_model_entry_changed(self, entry: Gtk.Entry) -> None:
        val = entry.get_text()
        self.settings_manager.set("ai_model", val)
        self._update_ai_config()

    def on_ai_model_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        # For editable combo, get_active_text() returns typed or selected text
        val = combo.get_active_text()
        if val:
            self.settings_manager.set("ai_model", val)
            self._update_ai_config()

    def _update_ai_config(self) -> None:
        sm = self.settings_manager
        self.ai_engine.configure(
            sm.get("ai_provider"), sm.get("ai_api_key"), sm.get("ai_model")
        )

    def _populate_ai_models(self, provider: str) -> None:
        """Populate the model combo with known models for the selected provider."""
        self.combo_ai_model.remove_all()

        models = []
        if provider == "gemini":
            models = [
                "gemini-2.5-flash", "gemini-3-pro",
                "gemini-1.5-pro", "gemini-1.5-flash"
            ]
        elif provider == "openai":
            models = ["gpt-4o", "gpt-5.2", "gpt-3.5-turbo"]

        for m in models:
            self.combo_ai_model.append_text(m)

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

        # Populate models for current provider
        self._populate_ai_models(ai_prov)

        # Smart default model if not set
        current_model = sm.get("ai_model")
        if not current_model:
            if ai_prov == "gemini":
                current_model = "gemini-2.5-flash"
            else:
                current_model = "gpt-4o"

        # Combo entry
        child = self.combo_ai_model.get_child()
        if isinstance(child, Gtk.Entry):
            child.set_text(current_model)
        elif hasattr(self.combo_ai_model, "set_active_id"):
             # Fallback if text entry manipulation fails, try active id if it matches
             # But here we want custom text too.
             pass

        # Set text directly if possible via the entry child of the combo
        # GtkComboBoxText with has-entry=True has an internal GtkEntry
        entry = self.combo_ai_model.get_child()
        if entry and isinstance(entry, Gtk.Entry):
            entry.set_text(current_model)

        # Configure initial AI engine state
        self.ai_engine.configure(ai_prov, sm.get("ai_api_key"), current_model)

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

    @staticmethod
    def _format_bytes(b: int) -> str:
        """Human-readable byte size (e.g. '4.2 GB')."""
        if b <= 0:
            return "0 B"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(b) < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024.0
        return f"{b:.1f} PB"

    @staticmethod
    def _severity_for(value: float) -> str:
        """Return severity tier: normal / warning / danger."""
        if value >= 90:
            return "danger"
        elif value >= 70:
            return "warning"
        return "normal"

    def _apply_meter_severity(
        self, container: Gtk.Widget, level_bar: Gtk.LevelBar,
        val_label: Gtk.Label, value: float,
    ) -> None:
        """Color-code a level-bar + label based on severity."""
        sev = self._severity_for(value)
        ctx = container.get_style_context()
        for cls in ("meter-normal", "meter-warning", "meter-danger"):
            ctx.remove_class(cls)
        ctx.add_class(f"meter-{sev}")

        val_ctx = val_label.get_style_context()
        for cls in ("resource-label-normal", "resource-label-warning", "resource-label-danger"):
            val_ctx.remove_class(cls)
        val_ctx.add_class(f"resource-label-{sev}")

    def _on_health_tick(self) -> bool:
        metrics = self.health_engine.get_metrics()
        status = self.health_engine.get_detailed_status()

        cpu = metrics['cpu']
        ram = metrics['ram']
        disk = metrics['disk']
        score = metrics['score']
        ram_used = metrics.get('ram_used', 0)
        ram_total = metrics.get('ram_total', 0)
        disk_used = metrics.get('disk_used', 0)
        disk_total = metrics.get('disk_total', 0)
        cpu_count = metrics.get('cpu_count', 1)
        cpu_freq = metrics.get('cpu_freq_max', 0)

        # ── Dashboard meters (compact view) ──
        self.lbl_dash_cpu_val.set_text(f"{cpu:.0f}%")
        self.lbl_dash_ram_val.set_text(
            f"{self._format_bytes(ram_used)} / {self._format_bytes(ram_total)}"
        )
        self.lbl_dash_disk_val.set_text(
            f"{self._format_bytes(disk_used)} / {self._format_bytes(disk_total)}"
        )
        self.level_dash_cpu.set_value(cpu)
        self.level_dash_ram.set_value(ram)
        self.level_dash_disk.set_value(disk)

        # Apply severity colours on dashboard meters
        self._apply_meter_severity(
            self.level_dash_cpu.get_parent(), self.level_dash_cpu,
            self.lbl_dash_cpu_val, cpu,
        )
        self._apply_meter_severity(
            self.level_dash_ram.get_parent(), self.level_dash_ram,
            self.lbl_dash_ram_val, ram,
        )
        self._apply_meter_severity(
            self.level_dash_disk.get_parent(), self.level_dash_disk,
            self.lbl_dash_disk_val, disk,
        )

        # ── Dashboard score card ──
        self.lbl_score_value.set_text(str(int(score)))
        self.lbl_score_status.set_text(status)
        self._set_score_detail(score)
        self._apply_score_colour(score)

        # ── Health page (detailed view) ──
        self.lbl_health_score_big.set_text(str(int(score)))
        self.lbl_health_status_text.set_text(f"{_('health_score_label')} — {status}")

        # CPU detail
        freq_str = f" @ {cpu_freq/1000:.1f} GHz" if cpu_freq > 0 else ""
        self.lbl_health_cpu_val.set_text(
            f"{cpu:.1f}%  ({cpu_count} {_('health_cores')}{freq_str})"
        )
        self.level_health_cpu.set_value(cpu)
        # RAM detail
        self.lbl_health_ram_val.set_text(
            f"{ram:.1f}%  ({self._format_bytes(ram_used)} / {self._format_bytes(ram_total)})"
        )
        self.level_health_ram.set_value(ram)
        # Disk detail
        disk_free = disk_total - disk_used if disk_total > disk_used else 0
        self.lbl_health_disk_val.set_text(
            f"{disk:.1f}%  ({self._format_bytes(disk_used)} / {self._format_bytes(disk_total)}, "
            f"{self._format_bytes(disk_free)} {_('health_free')})"
        )
        self.level_health_disk.set_value(disk)

        # Apply severity colours on health meters
        self._apply_meter_severity(
            self.level_health_cpu.get_parent(), self.level_health_cpu,
            self.lbl_health_cpu_val, cpu,
        )
        self._apply_meter_severity(
            self.level_health_ram.get_parent(), self.level_health_ram,
            self.lbl_health_ram_val, ram,
        )
        self._apply_meter_severity(
            self.level_health_disk.get_parent(), self.level_health_disk,
            self.lbl_health_disk_val, disk,
        )

        return True  # keep the timer alive

    def _apply_score_colour(self, score: float) -> None:
        """Color-code the score label based on value."""
        ctx = self.lbl_score_value.get_style_context()
        for cls in ("score-excellent", "score-good", "score-fair", "score-critical"):
            ctx.remove_class(cls)
        if score >= 90:
            ctx.add_class("score-excellent")
        elif score >= 70:
            ctx.add_class("score-good")
        elif score >= 50:
            ctx.add_class("score-fair")
        else:
            ctx.add_class("score-critical")
        # Also apply on health page big score
        ctx2 = self.lbl_health_score_big.get_style_context()
        for cls in ("score-excellent", "score-good", "score-fair", "score-critical"):
            ctx2.remove_class(cls)
        ctx2.add_class(ctx.list_classes()[-1] if ctx.list_classes() else "score-good")

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

        # Pardus / Debian diagnostics
        pardus_results = self.pardus_analyzer.run_full_diagnostics()

        # Security audit
        security_results = self.security_scanner.run_full_scan()

        ai_insight = self.ai_engine.generate_insight(
            metrics, failed_services, errors_24h
        )

        GLib.idle_add(
            self._display_insights, recs, ai_insight, large_files,
            failed_services, slow_services, errors_24h, pardus_results,
            security_results
        )

    def _display_insights(
        self,
        recs: list,
        ai_insight: str,
        large_files: list,
        failed_services: list,
        slow_services: list,
        errors_24h: int,
        pardus_results: dict = None,
        security_results: dict = None,
    ) -> None:
        # Clear container
        for child in self.box_insights_container.get_children():
            if child == self.box_insights_placeholder:
                child.set_visible(False)
            else:
                self.box_insights_container.remove(child)

        has_content = False

        # ── Pardus / Debian Diagnostics ──
        if pardus_results:
            # Broken packages
            broken_data = pardus_results.get("broken_packages", {})
            broken = broken_data.get("packages", []) if isinstance(broken_data, dict) else broken_data
            if broken:
                has_content = True
                self._add_section_header(
                    f"{_('pardus_broken_packages')} ({len(broken)})"
                )
                for pkg in broken:
                    self._add_insight_card(
                        str(pkg), "dialog-error-symbolic", "error",
                        "fix_broken", _("btn_fix_now"),
                    )

            # Repository health
            repo = pardus_results.get("repo_health", {})
            repo_issues = repo.get("issues", [])
            if repo_issues:
                has_content = True
                self._add_section_header(_("pardus_repo_health"))
                for issue in repo_issues:
                    self._add_insight_card(
                        issue, "software-update-available-symbolic",
                        "warning", None, None,
                    )

            # Available updates
            updates_data = pardus_results.get("available_updates", {})
            updates = updates_data.get("packages", []) if isinstance(updates_data, dict) else updates_data
            if updates:
                has_content = True
                count = len(updates)
                header = f"{_('pardus_updates_available')}: {count}"
                self._add_section_header(header)
                for upd in updates[:10]:  # Show at most 10
                    self._add_insight_card(
                        str(upd), "software-update-available-symbolic",
                        "info", None, None,
                    )

            # Held packages
            held = pardus_results.get("held_packages", [])
            if held:
                has_content = True
                self._add_section_header(
                    f"{_('pardus_held_packages')} ({len(held)})"
                )
                for pkg in held:
                    self._add_insight_card(
                        pkg, "changes-prevent-symbolic", "warning",
                        None, None,
                    )

            # Pardus-specific services (list of dicts with name/installed/status)
            pardus_svcs = pardus_results.get("pardus_services", [])
            if isinstance(pardus_svcs, list):
                missing_svcs = [
                    s["name"] for s in pardus_svcs
                    if isinstance(s, dict) and s.get("status") != "installed"
                ]
            else:
                missing_svcs = []

            # Systemd failed units from service dependency graph
            svc_deps = pardus_results.get("service_dependencies", {})
            failed_units = svc_deps.get("failed", []) if isinstance(svc_deps, dict) else []

            if missing_svcs or failed_units:
                has_content = True
                self._add_section_header(_("pardus_service_issues"))
                for name in missing_svcs:
                    self._add_insight_card(
                        f"{name} — {_('pardus_svc_not_installed')}",
                        "dialog-warning-symbolic", "warning",
                        None, None,
                    )
                for unit in failed_units:
                    self._add_insight_card(
                        unit, "dialog-error-symbolic", "error",
                        "view_services", _("btn_view_svcs"),
                    )

        # ── Security Audit ──
        if security_results:
            summary = security_results.get("summary", {})
            total_issues = summary.get("total_issues", 0)

            if total_issues > 0:
                has_content = True
                self._add_section_header(
                    f"{_('security_title')} — "
                    + _("security_scan_summary")
                    .replace("{total}", str(total_issues))
                    .replace("{critical}", str(summary.get("critical", 0)))
                    .replace("{high}", str(summary.get("high", 0)))
                    .replace("{warning}", str(summary.get("warning", 0)))
                )

                for item in security_results.get("world_writable", [])[:10]:
                    self._add_insight_card(
                        f"{_('security_world_writable')}: {item['path']}",
                        "dialog-warning-symbolic", "warning", None, None,
                    )
                for item in security_results.get("suid_binaries", [])[:10]:
                    self._add_insight_card(
                        f"{_('security_suid_binaries')}: {item['path']}",
                        "dialog-error-symbolic", "error", None, None,
                    )
                for item in security_results.get("sudoers_audit", []):
                    self._add_insight_card(
                        f"{_('security_sudoers_risk')}: {item.get('content', '')}",
                        "dialog-error-symbolic", "error", None, None,
                    )
                for item in security_results.get("ssh_config", []):
                    self._add_insight_card(
                        f"{_('security_ssh_issues')}: {item['recommendation']}",
                        "dialog-warning-symbolic", item.get("severity", "warning"),
                        None, None,
                    )

                ua = security_results.get("unattended_upgrades", {})
                if not ua.get("enabled", False) and ua.get("installed", False):
                    self._add_insight_card(
                        _("security_unattended_disabled"),
                        "software-update-urgent-symbolic", "warning",
                        None, None,
                    )

                logins = security_results.get("failed_logins", {})
                login_count = logins.get("count", 0)
                if login_count > 10:
                    sev = "error" if login_count > 50 else "warning"
                    self._add_insight_card(
                        _("security_failed_logins_detail").replace(
                            "{count}", str(login_count)
                        ),
                        "dialog-password-symbolic", sev, "analyze_logs",
                        _("btn_view_logs"),
                    )

            # Repo trust score (from pardus_results)
            if pardus_results:
                trust = pardus_results.get("repo_trust_score", {})
                trust_score = trust.get("score", 100)
                if trust_score < 80:
                    has_content = True
                    self._add_section_header(_("security_repo_trust"))
                    self._add_insight_card(
                        _("security_repo_trust_detail").replace(
                            "{score}", str(trust_score)
                        ),
                        "security-medium-symbolic",
                        "warning" if trust_score >= 50 else "error",
                        None, None,
                    )
                    for detail in trust.get("details", []):
                        self._add_insight_card(
                            detail.get("message", ""),
                            "dialog-warning-symbolic",
                            detail.get("severity", "info"),
                            None, None,
                        )

                # Repair simulation
                repair = pardus_results.get("repair_simulation", {})
                needs_repair = (
                    repair.get("fix_broken", {}).get("changes_needed", False)
                    or repair.get("autoremove", {}).get("changes_needed", False)
                )
                if needs_repair:
                    has_content = True
                    removable = repair.get("autoremove", {}).get(
                        "removable_count", 0
                    )
                    self._add_insight_card(
                        _("security_repair_desc").replace(
                            "{count}", str(removable)
                        ),
                        "emblem-system-symbolic", "info",
                        "fix_broken", _("btn_fix_now"),
                    )

        # Recommendations
        if recs:
            has_content = True
            self._add_section_header(_("insights_recommendations"))
            for r in recs:
                level = r['type'] # warning or error
                icon = "dialog-warning-symbolic" if level == 'warning' else "dialog-error-symbolic"
                action = r.get('action')
                # Determine smart label
                label = _("btn_fix_now")
                if action == "clean_disk": label = _("btn_clean_disk")
                elif action == "open_system_monitor": label = _("btn_sys_mon")
                elif action == "view_services": label = _("btn_view_svcs")
                elif action == "optimize_ram": label = _("btn_fix_now")

                self._add_insight_card(r['message'], icon, level, action, label)

        # Failed services
        if failed_services:
            has_content = True
            self._add_section_header(f"{_('insights_failed_services')} ({len(failed_services)})")
            for svc in failed_services:
                self._add_insight_card(
                    svc, "service-template-symbolic", "error", "view_services", _("btn_view_svcs")
                )

        # Slow boot services
        if slow_services:
            has_content = True
            self._add_section_header(_("insights_slow_boot"))
            for s in slow_services:
                self._add_insight_card(
                    f"{s['service']} ({s['time']})", "speedometer-symbolic", "warning", "view_services", _("btn_inspect")
                )

        # Errors
        if errors_24h > 0:
            has_content = True
            self._add_section_header(f"{_('insights_journal_errors')}: {errors_24h}")
            self._add_insight_card(
                _('insights_journal_errors_detail').replace('{count}', str(errors_24h)),
                "dialog-error-symbolic", "error", "analyze_logs", _("btn_view_logs")
            )

        # Large files
        if large_files:
            has_content = True
            self._add_section_header(_("insights_large_files"))
            for f in large_files:
                self._add_insight_card(
                    f"{f['size']} - {f['path']}", "folder-symbolic", "info", "clean_disk", _("btn_clean_disk")
                )

        # AI Insight
        if ai_insight and "disabled" not in ai_insight:
            has_content = True
            self._add_section_header(_("insights_ai"))

            # Formatted AI Card
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.set_visible(True)
            card.get_style_context().add_class("card")
            card.set_margin_bottom(12)
            card.set_margin_start(4)
            card.set_margin_end(4)
            card.set_border_width(12)

            # Process Markdown-style headers to Pango Markup
            # 1. Bold headers (Summary:, Analysis:, etc.)
            formatted_text = GLib.markup_escape_text(ai_insight)
            for header in ["Summary:", "Analysis:", "Actions:", "Executive Summary:", "Critical Analysis:", "Action Plan:"]:
                formatted_text = formatted_text.replace(header, f"<b>{header}</b>")

            # 2. Bullet points to fancy bullets
            formatted_text = formatted_text.replace("- ", "• ").replace("* ", "• ")

            lbl = Gtk.Label()
            lbl.set_markup(f"<span font_desc='Sans 10'>{formatted_text}</span>")
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

    def _add_insight_card(self, message: str, icon_name: str, level: str = "info", action_id: str = None, action_label: str = None) -> None:
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

        # Label container (VBox)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_visible(True)
        box.pack_start(vbox, True, True, 0)

        # Label
        lbl = Gtk.Label(label=message)
        lbl.set_visible(True)
        lbl.set_xalign(0)
        lbl.set_line_wrap(True)
        vbox.pack_start(lbl, True, True, 0)

        # Action Button (only if action_id provided)
        if action_id:
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            btn_box.set_visible(True)
            # Use specific label if provided, else fallback
            btn_text = action_label or "Fix Now"
            btn = Gtk.Button(label=btn_text)
            btn.set_visible(True)
            btn.get_style_context().add_class("suggested-action") # CSS class for styling
            btn.set_halign(Gtk.Align.END)
            # Use a lambda that captures the current action_id text
            btn.connect("clicked", lambda b, a=action_id: self._on_action_clicked(a))
            btn_box.pack_end(btn, False, False, 0)
            vbox.pack_start(btn_box, False, False, 0)

        self.box_insights_container.add(box)

    def _on_action_clicked(self, action_id: str) -> None:
        """Handle insight action buttons."""
        if action_id == "clean_disk":
            self.content_stack.set_visible_child_name("page_cleaner")
        elif action_id == "open_system_monitor":
            self.content_stack.set_visible_child_name("page_health")
        elif action_id == "view_services":
             # Simple dialog for now as we don't have a service manager view
             self._show_simple_dialog("Service Manager", "Run 'systemctl --failed' in a terminal to inspect failed services.")
        elif action_id == "optimize_ram":
             self._set_info("Optimizing RAM caches... (Simulated)", "info")
             # In real app: could run 'sync; echo 3 > /proc/sys/vm/drop_caches' with pkexec
        elif action_id == "analyze_logs":
             self._show_simple_dialog("System Logs", "Check journalctl -xe or /var/log/syslog for details.")
        else:
             logger.warning("Unknown action: %s", action_id)

    def _show_simple_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


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
