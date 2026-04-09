#!/usr/bin/env python3
"""GTK3 Stopwatch with lap support."""
import os
import signal
import sys
import time
import gi

# Double-fork to fully detach from terminal
if os.fork() != 0:
    sys.exit(0)
os.setsid()
if os.fork() != 0:
    sys.exit(0)
# Redirect stdio to /dev/null so nothing ties us to the old terminal
devnull = os.open(os.devnull, os.O_RDWR)
for fd in (0, 1, 2):
    os.dup2(devnull, fd)
os.close(devnull)
signal.signal(signal.SIGINT, signal.SIG_IGN)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk


def fmt(s):
    m, s = divmod(s, 60)
    h, m = divmod(int(m), 60)
    cs = int((s % 1) * 100)
    s = int(s)
    if h:
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
    return f"{m:02d}:{s:02d}.{cs:02d}"


class Stopwatch(Gtk.Window):
    def __init__(self):
        super().__init__(title="Stopwatch")
        self.set_default_size(380, 500)
        self.set_resizable(True)

        self.running = False
        self.start_t = 0.0
        self.elapsed = 0.0
        self.laps = []
        self.last_lap = 0.0
        self.timer_id = None

        self._apply_css()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_name("main")
        self.add(vbox)

        # Time display
        self.time_label = Gtk.Label(label="00:00.00")
        self.time_label.set_name("time-display")
        self.time_label.set_margin_top(40)
        self.time_label.set_margin_bottom(4)
        vbox.pack_start(self.time_label, False, False, 0)

        # Live lap split display
        self.lap_label = Gtk.Label(label="")
        self.lap_label.set_name("lap-display")
        self.lap_label.set_margin_bottom(20)
        vbox.pack_start(self.lap_label, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_bottom(20)

        self.reset_btn = Gtk.Button(label="Reset")
        self.reset_btn.set_name("reset-btn")
        self.reset_btn.set_size_request(110, 44)
        self.reset_btn.set_sensitive(False)
        self.reset_btn.connect("clicked", self._on_reset)

        self.main_btn = Gtk.Button(label="Start")
        self.main_btn.set_name("start-btn")
        self.main_btn.set_size_request(110, 44)
        self.main_btn.connect("clicked", self._on_main)

        btn_box.pack_start(self.reset_btn, False, False, 0)
        btn_box.pack_start(self.main_btn, False, False, 0)
        vbox.pack_start(btn_box, False, False, 0)

        # Lap list
        sep = Gtk.Separator()
        sep.set_name("lap-sep")
        vbox.pack_start(sep, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.lap_store = Gtk.ListStore(int, str, str)  # num, split, total
        self.lap_view = Gtk.TreeView(model=self.lap_store)
        self.lap_view.set_headers_visible(True)
        self.lap_view.set_name("lap-list")
        self.lap_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        for i, title in enumerate(["Lap", "Split", "Total"]):
            renderer = Gtk.CellRendererText()
            renderer.set_padding(12, 6)
            if i == 0:
                renderer.set_property("foreground", "#666666")
            col = Gtk.TreeViewColumn(title, renderer)
            if i == 0:
                col.add_attribute(renderer, "text", 0)
            else:
                col.add_attribute(renderer, "text", i)
                col.add_attribute(renderer, "foreground", i)
            col.set_expand(True)
            self.lap_view.append_column(col)

        # Custom cell rendering for colors
        self.lap_view.get_column(1).set_cell_data_func(
            self.lap_view.get_column(1).get_cells()[0], self._render_split
        )
        self.lap_view.get_column(2).get_cells()[0].set_property("foreground", "#888888")

        # Right-click menu for copy
        self.lap_view.connect("button-press-event", self._on_lap_click)

        scroll.add(self.lap_view)
        vbox.pack_start(scroll, True, True, 0)

        # Keyboard shortcuts
        self.connect("key-press-event", self._on_key)
        self.connect("destroy", Gtk.main_quit)
        self.show_all()

    def _apply_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            #main { background: #0a0a0f; }
            #time-display {
                font-family: monospace;
                font-size: 52px;
                font-weight: 300;
                color: #f0f0f0;
            }
            #lap-display {
                font-family: monospace;
                font-size: 22px;
                font-weight: 300;
                color: #888888;
            }
            button {
                font-family: monospace;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 1px;
                border-radius: 25px;
                border: none;
                padding: 8px 20px;
            }
            #start-btn { background: #1a6b3c; color: #4ade80; }
            #start-btn:hover { background: #1e7a44; }
            #stop-btn { background: #6b1a1a; color: #f87171; }
            #stop-btn:hover { background: #7a1e1e; }
            #reset-btn { background: #1e1e2a; color: #aaaaaa; }
            #reset-btn:hover { background: #2a2a3a; color: #cccccc; }
            #reset-btn:disabled { background: #141418; color: #444444; }
            #lap-sep { background: #1a1a25; min-height: 1px; }
            #lap-list {
                background: #0a0a0f;
                color: #cccccc;
                font-family: monospace;
                font-size: 13px;
            }
            #lap-list header button {
                background: #0a0a0f;
                color: #666666;
                font-size: 12px;
                border-radius: 0;
                border-bottom: 1px solid #1a1a25;
            }
            treeview.view {
                background-color: #0a0a0f;
                color: #cccccc;
            }
            treeview.view:selected {
                background-color: #0a0a0f;
                color: #cccccc;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _render_split(self, column, cell, model, iter_, data):
        if len(self.laps) < 2:
            cell.set_property("foreground", "#cccccc")
            return
        row = model.get_path(iter_).get_indices()[0]
        lap_idx = len(self.laps) - 1 - row
        split = self.laps[lap_idx][1]
        splits = [l[1] for l in self.laps]
        best, worst = min(splits), max(splits)
        if split == best:
            cell.set_property("foreground", "#4ade80")
        elif split == worst:
            cell.set_property("foreground", "#f87171")
        else:
            cell.set_property("foreground", "#cccccc")

    def _now(self):
        if self.running:
            return self.elapsed + (time.monotonic() - self.start_t)
        return self.elapsed

    def _tick(self):
        now = self._now()
        self.time_label.set_text(fmt(now))
        if self.laps:
            self.lap_label.set_text("lap " + fmt(now - self.last_lap))
        return self.running

    def _on_main(self, _=None):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.start_t = time.monotonic()
        self.main_btn.set_label("Stop")
        self.main_btn.set_name("stop-btn")
        self.reset_btn.set_label("Lap")
        self.reset_btn.set_sensitive(True)
        self.timer_id = GLib.timeout_add(33, self._tick)

    def _stop(self):
        self.running = False
        self.elapsed += time.monotonic() - self.start_t
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.time_label.set_text(fmt(self.elapsed))
        if self.laps:
            self.lap_label.set_text("lap " + fmt(self.elapsed - self.last_lap))
        self.main_btn.set_label("Start")
        self.main_btn.set_name("start-btn")
        self.reset_btn.set_label("Reset")

    def _on_reset(self, _=None):
        if self.running:
            self._lap()
        elif self.elapsed > 0:
            self._reset()

    def _lap(self):
        now = self._now()
        split = now - self.last_lap
        self.last_lap = now
        self.laps.append((now, split))
        self.lap_store.prepend([len(self.laps), fmt(split), fmt(now)])

    def _reset(self):
        self.elapsed = 0.0
        self.last_lap = 0.0
        self.laps.clear()
        self.lap_store.clear()
        self.time_label.set_text("00:00.00")
        self.lap_label.set_text("")
        self.reset_btn.set_sensitive(False)

    def _copy_laps(self):
        if not self.laps:
            return
        lines = ["Lap\tSplit\tTotal"]
        for i, (total, split) in enumerate(self.laps, 1):
            lines.append(f"{i}\t{fmt(split)}\t{fmt(total)}")
        text = "\n".join(lines)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    def _on_lap_click(self, widget, event):
        if event.button == 3 and self.laps:
            menu = Gtk.Menu()
            item = Gtk.MenuItem(label="Copy All Laps")
            item.connect("activate", lambda _: self._copy_laps())
            menu.append(item)
            menu.show_all()
            menu.popup_at_pointer(event)

    def _on_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "space":
            self._on_main()
        elif key in ("l", "L") and self.running:
            self._lap()
        elif key in ("r", "R") and not self.running:
            self._reset()
        elif key in ("q", "Q"):
            Gtk.main_quit()
        elif event.state & Gdk.ModifierType.CONTROL_MASK and key in ("c", "C"):
            self._copy_laps()


if __name__ == "__main__":
    Stopwatch()
    Gtk.main()
