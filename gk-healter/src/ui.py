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
from gi.repository import Gtk, GLib, Gdk

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
        self.lbl_score_value: Gtk.Label = g("lbl_score_value")
        self.lbl_score_status: Gtk.Label = g("lbl_score_status")
        self.lbl_score_detail: Gtk.Label = g("lbl_score_detail")
        self.lbl_dash_cpu_val: Gtk.Label = g("lbl_dash_cpu_val")
        self.lbl_dash_ram_val: Gtk.Label = g("lbl_dash_ram_val")
        self.lbl_dash_disk_val: Gtk.Label = g("lbl_dash_disk_val")
        self.level_dash_cpu: Gtk.LevelBar = g("level_dash_cpu")
        self.level_dash_ram: Gtk.LevelBar = g("level_dash_ram")
        self.level_dash_disk: Gtk.LevelBar = g("level_dash_disk")
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
        self.lbl_health_score_big: Gtk.Label = g("lbl_health_score_big")
        self.lbl_health_status_text: Gtk.Label = g("lbl_health_status_text")
        self.lbl_health_cpu_val: Gtk.Label = g("lbl_health_cpu_val")
        self.lbl_health_ram_val: Gtk.Label = g("lbl_health_ram_val")
        self.lbl_health_disk_val: Gtk.Label = g("lbl_health_disk_val")
        self.level_health_cpu: Gtk.LevelBar = g("level_health_cpu")
        self.level_health_ram: Gtk.LevelBar = g("level_health_ram")
        self.level_health_disk: Gtk.LevelBar = g("level_health_disk")

        # ── Insights ──
        self.txt_insights: Gtk.TextView = g("txt_insights")

        # ── History ──
        self.history_list_store: Gtk.ListStore = g("history_list_store")

        # ── Settings ──
        self.combo_language: Gtk.ComboBoxText = g("combo_language")
        self.switch_auto_maintenance: Gtk.Switch = g("switch_auto_maintenance")
        self.box_auto_settings: Gtk.Box = g("box_auto_settings")
        self.combo_frequency: Gtk.ComboBoxText = g("combo_frequency")
        self.spin_idle: Gtk.SpinButton = g("spin_idle")
        self.switch_ac_power: Gtk.Switch = g("switch_ac_power")
        self.switch_notify: Gtk.Switch = g("switch_notify")
        self.switch_disk_threshold: Gtk.Switch = g("switch_disk_threshold")
        self.spin_disk_percent: Gtk.SpinButton = g("spin_disk_percent")
        self.lbl_last_maintenance: Gtk.Label = g("lbl_last_maintenance")

        # ── Dialogs ──
        self.about_dialog: Gtk.AboutDialog = g("about_dialog")
        self.clean_confirm_dialog: Gtk.MessageDialog = g("clean_confirm_dialog")

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
    def on_refresh_insights_clicked(self, _btn: Optional[Gtk.Button]) -> None:
        buf = self.txt_insights.get_buffer()
        buf.set_text(_("msg_analyzing"))
        threading.Thread(target=self._run_analysis, daemon=True).start()

    # ── Settings page ────────────────────────────────────────────────────────
    def on_language_changed(self, combo: Gtk.ComboBoxText) -> None:
        lang_id = combo.get_active_id()
        if lang_id:
            self.settings_manager.set("language", lang_id)
            I18nManager().load_language(lang_id)

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

    # ══════════════════════════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    # ── Settings initialisation ──────────────────────────────────────────────
    def _init_settings_ui(self) -> None:
        """Populate combo-boxes and restore saved values into the Settings page."""
        sm = self.settings_manager

        # Language combo
        self.combo_language.append("auto", "Auto")
        self.combo_language.append("en", "English")
        self.combo_language.append("tr", "Türkçe")
        current_lang = sm.get("language") or "auto"
        self.combo_language.set_active_id(current_lang)

        # Frequency combo
        self.combo_frequency.append("1", _("freq_daily"))
        self.combo_frequency.append("7", _("freq_weekly"))
        self.combo_frequency.append("14", _("freq_biweekly"))
        self.combo_frequency.append("30", _("freq_monthly"))
        freq = str(sm.get("maintenance_frequency_days"))
        self.combo_frequency.set_active_id(freq)

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
        self.lbl_health_status_text.set_text(f"Health Score — {status}")
        self.lbl_health_cpu_val.set_text(f"{cpu:.0f}%")
        self.lbl_health_ram_val.set_text(f"{ram:.0f}%")
        self.lbl_health_disk_val.set_text(f"{disk:.0f}%")
        self.level_health_cpu.set_value(cpu)
        self.level_health_ram.set_value(ram)
        self.level_health_disk.set_value(disk)

        return True  # keep the timer alive

    def _set_score_detail(self, score: float) -> None:
        if score >= 90:
            self.lbl_score_detail.set_text(
                "All systems running smoothly. No action needed."
            )
        elif score >= 70:
            self.lbl_score_detail.set_text(
                "System is mostly healthy. Minor resource pressure detected."
            )
        elif score >= 50:
            self.lbl_score_detail.set_text(
                "Moderate resource usage. Consider closing unused applications."
            )
        else:
            self.lbl_score_detail.set_text(
                "High resource usage detected. Immediate attention recommended."
            )

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
        lines: List[str] = []

        # Header
        lines.append("═══  System Insights  ═══\n")

        # Recommendations
        if recs:
            lines.append("▸ Recommendations")
            for r in recs:
                icon = "⚠" if r['type'] == 'warning' else "✖"
                lines.append(f"  {icon}  {r['message']}")
            lines.append("")

        # Failed services
        if failed_services:
            lines.append(f"▸ Failed Services ({len(failed_services)})")
            for svc in failed_services:
                lines.append(f"  •  {svc}")
            lines.append("")

        # Slow boot services
        if slow_services:
            lines.append("▸ Slow Boot Services")
            for s in slow_services:
                lines.append(f"  •  {s['service']}  ({s['time']})")
            lines.append("")

        # Errors
        lines.append(f"▸ Journal Errors (24h): {errors_24h}\n")

        # Large files
        if large_files:
            lines.append("▸ Large Files (>100 MB)")
            for f in large_files:
                lines.append(f"  •  {f['size']}  {f['path']}")
            lines.append("")

        # AI
        lines.append(f"▸ AI Insight\n  {ai_insight}")

        buf = self.txt_insights.get_buffer()
        buf.set_text("\n".join(lines))

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
        self.summary_label.set_text(f"Total: {format_size(total)}")

    def _set_info(self, message: str, level: str = "info") -> None:
        """Update the info-bar label and message type."""
        type_map = {
            "info": Gtk.MessageType.INFO,
            "warning": Gtk.MessageType.WARNING,
            "error": Gtk.MessageType.ERROR,
        }
        self.info_bar.set_message_type(type_map.get(level, Gtk.MessageType.INFO))
        self.info_label.set_text(message)
