"""CustomTkinter compatibility layer for manga_gui.

`install()` rebinds the plain tkinter/ttk widget names used throughout
manga_gui.py onto customtkinter widgets, so the app gets the CTk look
(rounded cards, flat surfaces, hover states) without rewriting the module.

The wrappers preserve the legacy API surface the app and the regression
suite rely on:

- subscript access: ``w["text"]``, ``w["bg"]``, ``bar["value"]``
- ``ttk.Combobox.current(i)`` (CTkComboBox has none)
- ``<<ComboboxSelected>>`` virtual event -> combo command callback
- ttk style strings / legacy kwargs (bg, fg, relief, highlightthickness,
  exportselection, ...) are accepted and mapped or ignored
- ``ThemedText`` / ``ThemedTree`` drop-in replacements for the two widgets
  CTk does not provide, themed from the shared palette

The palette (a dict of resolved hex colors, manga_gui's ``self.colors``)
is injected with ``set_palette`` before widgets are built and refreshed
on every theme rebuild.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

import customtkinter as ctk

# manga_gui imports ``tkinter as tk`` and uses tk.StringVar / tk.END / tk.W ...
# against this module's A alias, so those names keep resolving to tkinter.
A = tk


# ---------------------------------------------------------------------------
# palette + helpers
# ---------------------------------------------------------------------------

_PALETTE: dict[str, str] = {}
_TREES: list["ThemedTree"] = []


def set_palette(colors: dict[str, str]) -> None:
    """Feed the resolved theme colors (manga_gui ``self.colors``)."""
    _PALETTE.clear()
    _PALETTE.update(colors)
    restyle_trees()


def _hex(value, fallback=None):
    """Pass through hex colors; resolve palette keys; else fallback."""
    if not isinstance(value, str):
        return fallback
    if value.startswith("#"):
        return value
    resolved = _PALETTE.get(value)
    if isinstance(resolved, str) and resolved.startswith("#"):
        return resolved
    return fallback if fallback is not None else value


def _c(key: str, fallback: str) -> str:
    value = _PALETTE.get(key)
    if isinstance(value, (tuple, list)):
        value = value[0]
    return value if isinstance(value, str) and value.startswith("#") else fallback


def _blend(hex_a: str, hex_b: str, t: float) -> str:
    def channel(sa: str, sb: str) -> int:
        return round(int(sa, 16) * (1 - t) + int(sb, 16) * t)
    hex_a = hex_a.lstrip("#"); hex_b = hex_b.lstrip("#")
    return "#{:02x}{:02x}{:02x}".format(
        *(channel(hex_a[i:i + 2], hex_b[i:i + 2]) for i in (0, 2, 4)))


def _font(value, default=("Segoe UI", 13)):
    if value is None:
        return default
    if isinstance(value, tkfont.Font):
        actual = value.actual()
        weight = actual.get("weight", "normal")
        return (actual.get("family", "Segoe UI"), actual.get("size", 13),
                "bold" if weight == "bold" else "normal")
    if isinstance(value, (tuple, list)):
        parts = tuple(p for p in value if p)
        return parts if parts else default
    return default


def _px(chars) -> int | None:
    """Legacy char-width -> rough pixel width (avg glyph ~ 9 px @ Segoe 13)."""
    if chars is None:
        return None
    try:
        chars = int(chars)
    except (TypeError, ValueError):
        return None
    return max(32, chars * 9 + 16) if chars < 80 else int(chars)


_DEAD_WIDGET_KWARGS = (
    "style", "relief", "bd", "borderwidth", "highlightthickness",
    "highlightbackground", "highlightcolor", "takefocus", "cursor",
    "padx", "pady", "anchor_anchor", "padding",
)


# common base for the wrappers: lets every wrapper share the ``install``-era
# duck-typing helpers without colliding with CTk's own MRO
class _Base:
    pass


# ---------------------------------------------------------------------------
# frame
# ---------------------------------------------------------------------------

class CompatFrame(_Base, ctk.CTkFrame):
    def __init__(self, master=None, **kw):
        style = kw.pop("style", None)
        bg = kw.pop("bg", None) or kw.pop("background", None)
        for dead in _DEAD_WIDGET_KWARGS:
            kw.pop(dead, None)
        is_card = bool(style and "Card" in str(style)) or (
            isinstance(bg, str) and bg == _PALETTE.get("card"))
        if is_card:
            kw.setdefault("fg_color", _c("card", "#11151f"))
            kw.setdefault("border_width", 1)
            kw.setdefault("border_color", _c("border", "#222b3d"))
            kw.setdefault("corner_radius", 12)
        else:
            kw.setdefault("fg_color", _hex(bg) if bg else _c("bg", "#080b12"))
            kw.setdefault("corner_radius", 6)
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {"bg": self.cget("fg_color")}
        for dead in _DEAD_WIDGET_KWARGS:
            kw.pop(dead, None)
        kw.pop("bg", None)
        kw.pop("background", None)
        return super().configure(**kw)

    def __getitem__(self, key):
        if key in ("bg", "background"):
            try:
                return self.cget("fg_color")
            except Exception:
                return _c("bg", "#080b12")
        if key == "style":
            return ""
        return dict(bg=self.cget("fg_color")).get(key, "")

    def __setitem__(self, key, value):
        if key in ("bg", "background"):
            self.configure(fg_color=value)
        # style / relief / highlight* are accepted no-ops


# ---------------------------------------------------------------------------
# label
# ---------------------------------------------------------------------------

class CompatLabel(_Base, ctk.CTkLabel):
    def __init__(self, master=None, **kw):
        style = kw.pop("style", None)
        bg = kw.pop("bg", None) or kw.pop("background", None)
        fg = kw.pop("fg", None) or kw.pop("foreground", None)
        anchor = kw.pop("anchor", None)
        for dead in _DEAD_WIDGET_KWARGS:
            kw.pop(dead, None)
        kw.pop("justify", None)
        kw.pop("bitmap", None)
        if style:
            if "Title" in str(style):
                kw.setdefault("font", ("Segoe UI", 22, "bold"))
            elif "CardTitle" in str(style):
                kw.setdefault("font", ("Segoe UI", 12, "bold"))
            elif "Muted" in str(style):
                fg = fg or _c("muted", "#7e89a6")
        if bg:
            kw.setdefault("fg_color", _hex(bg))
        else:
            kw.setdefault("fg_color", "transparent")
        if fg:
            kw.setdefault("text_color", _hex(fg))
        kw.setdefault("font", _font(kw.pop("font", None)))
        if anchor is not None:
            kw.setdefault("anchor", anchor)
        self._has_var = kw.get("textvariable") is not None
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        for dead in _DEAD_WIDGET_KWARGS:
            kw.pop(dead, None)
        bg = kw.pop("bg", None) or kw.pop("background", None)
        fg = kw.pop("fg", None) or kw.pop("foreground", None)
        if bg:
            kw["fg_color"] = bg if str(bg).startswith("#") else _c(str(bg), "#000000")
        if fg:
            kw["text_color"] = fg if str(fg).startswith("#") else _c(str(fg), "#ffffff")
        if self._has_var and "text" in kw:
            # a textvariable drives the label; silent text writes would fight it
            kw.pop("text")
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "text":
            return self.cget("text")
        if key in ("bg", "background"):
            try:
                value = self.cget("fg_color")
            except Exception:
                value = None
            return value if isinstance(value, str) and value.startswith("#") else _c("bg", "#080b12")
        if key in ("fg", "foreground"):
            try:
                value = self.cget("text_color")
            except Exception:
                value = None
            return value if isinstance(value, str) and value.startswith("#") else _c("text", "#e8eef7")
        if key == "font":
            return self.cget("font")
        if key == "anchor":
            return self.cget("anchor")
        if key == "state":
            return "normal"
        if key == "wraplength":
            return self.cget("wraplength")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})


# ---------------------------------------------------------------------------
# button
# ---------------------------------------------------------------------------

class CompatButton(_Base, ctk.CTkButton):
    def __init__(self, master=None, **kw):
        style = kw.pop("style", None)
        bg = kw.pop("bg", None) or kw.pop("background", None)
        fg = kw.pop("fg", None) or kw.pop("foreground", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "activebackground", "activeforeground", "disabledforeground",
                "overrelief", "default", "repeatdelay", "repeatinterval"):
            kw.pop(dead, None)
        width = kw.get("width")
        if width is not None:
            kw["width"] = _px(width) or width
        accent = bool(style and "Accent" in str(style))
        self._accent = accent
        if accent:
            kw.setdefault("fg_color", _c("accent_strong", "#6f52ee"))
            kw.setdefault("hover_color", _c("accent_press", "#5f45d6"))
            kw.setdefault("text_color", "#ffffff")
        else:
            base = _hex(bg) if bg else _blend(_c("text", "#e8eef7"), _c("card", "#11151f"), 0.06)
            kw.setdefault("fg_color", base)
            kw.setdefault("hover_color", _blend(_c("text", "#e8eef7"), _c("card", "#11151f"), 0.12))
            kw.setdefault("text_color", _hex(fg, _c("text", "#e8eef7")))
        kw.setdefault("corner_radius", 10)
        kw.setdefault("font", _font(kw.pop("font", None), ("Segoe UI", 12, "bold")))
        state = kw.pop("state", None)
        if state == "disabled":
            kw["state"] = "disabled"
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        for dead in _DEAD_WIDGET_KWARGS + (
                "activebackground", "activeforeground", "disabledforeground",
                "overrelief", "default"):
            kw.pop(dead, None)
        bg = kw.pop("bg", None) or kw.pop("background", None)
        fg = kw.pop("fg", None) or kw.pop("foreground", None)
        style = kw.pop("style", None)
        if style and "Accent" in str(style) and "fg_color" not in kw:
            kw["fg_color"] = _c("accent_strong", "#6f52ee")
            kw.setdefault("hover_color", _c("accent_press", "#5f45d6"))
        if bg:
            kw.setdefault("fg_color", bg)
        if fg:
            kw.setdefault("text_color", fg)
        width = kw.get("width")
        if width is not None:
            kw["width"] = _px(width) or width
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "state":
            return self.cget("state")
        if key == "text":
            return self.cget("text")
        if key in ("bg", "background"):
            return self.cget("fg_color")
        if key in ("fg", "foreground"):
            return self.cget("text_color")
        if key == "font":
            return self.cget("font")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

class CompatEntry(_Base, ctk.CTkEntry):
    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "insertbackground", "insertcolor", "insertwidth", "readonlybackground",
                "selectbackground", "selectforeground", "disabledbackground",
                "exportselection", "validate", "validatecommand", "invalidcommand",
                "disabledforeground", "highlight_bg"):
            kw.pop(dead, None)
        width = kw.pop("width", None)
        if width is not None:
            pw = _px(width)
            if pw:
                kw["width"] = pw
        state = kw.pop("state", None)
        self._readonly = state == "readonly"
        if state and not self._readonly:
            kw["state"] = state
        kw.setdefault("fg_color", _c("input", "#101623"))
        kw.setdefault("border_color", _c("border", "#222b3d"))
        kw.setdefault("text_color", _c("text", "#e8eef7"))
        kw.setdefault("corner_radius", 8)
        kw.setdefault("font", _font(kw.pop("font", None)))
        justify = kw.pop("justify", None)
        super().__init__(master, **kw)
        if justify and justify != "left":
            try:
                self._entry.configure(justify=justify)
            except Exception:
                pass

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "insertbackground", "insertcolor", "readonlybackground",
                "selectbackground", "selectforeground", "disabledbackground",
                "exportselection"):
            kw.pop(dead, None)
        state = kw.pop("state", None)
        if state is not None:
            self._readonly = state == "readonly"
            kw["state"] = "normal" if self._readonly else state
        bg = kw.pop("bg", None) or kw.pop("background", None)
        fg = kw.pop("fg", None) or kw.pop("foreground", None)
        if bg:
            kw.setdefault("fg_color", bg)
        if fg:
            kw.setdefault("text_color", fg)
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "state":
            return "readonly" if self._readonly else self.cget("state")
        if key == "textvariable":
            return self.cget("textvariable")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})


# ---------------------------------------------------------------------------
# combobox (adds .current(), maps <<ComboboxSelected>> -> command)
# ---------------------------------------------------------------------------

class CompatComboBox(_Base, ctk.CTkComboBox):
    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + ("exportselection",):
            kw.pop(dead, None)
        width = kw.pop("width", None)
        if width is not None:
            pw = _px(width)
            if pw:
                kw["width"] = pw
        state = kw.pop("state", None)
        if state:
            kw["state"] = state  # readonly supported by CTkComboBox
        if kw.get("textvariable") is not None and kw.get("variable") is None:
            kw["variable"] = kw.pop("textvariable")
        command = kw.get("command")
        if command is not None:
            kw["command"] = self._wrap_command(command)
        kw.setdefault("fg_color", _c("input", "#101623"))
        kw.setdefault("button_color", _c("input", "#101623"))
        kw.setdefault("button_hover_color", _blend(_c("input", "#101623"), _c("text", "#e8eef7"), 0.10))
        kw.setdefault("border_color", _c("border", "#222b3d"))
        kw.setdefault("text_color", _c("text", "#e8eef7"))
        kw.setdefault("dropdown_fg_color", _c("card", "#11151f"))
        kw.setdefault("dropdown_hover_color", _blend(_c("card", "#11151f"), _c("text", "#e8eef7"), 0.10))
        kw.setdefault("dropdown_text_color", _c("text", "#e8eef7"))
        kw.setdefault("corner_radius", 8)
        kw.setdefault("font", _font(kw.pop("font", None)))
        super().__init__(master, **kw)

    @staticmethod
    def _wrap_command(func):
        # ttk fires virtual events with no payload; CTk passes the selected value.
        def _fire(_value=None):
            try:
                return func()
            except TypeError:
                return func(tk.Event())
        return _fire

    def current(self, new=None):
        """ttk-compatible: index of the selected value, or select by index."""
        values = list(self.cget("values") or ())
        if new is None:
            try:
                return values.index(self.get())
            except ValueError:
                return -1
        if 0 <= new < len(values):
            self.set(values[new])  # silent, like ttk
        return None

    def bind(self, sequence=None, command=None, add=True):
        if sequence == "<<ComboboxSelected>>" and command is not None:
            self.configure(command=self._wrap_command(command))
            return None
        return super().bind(sequence, command, add)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + ("exportselection",):
            kw.pop(dead, None)
        if "command" in kw and kw["command"] is not None:
            kw["command"] = self._wrap_command(kw["command"])
        state = kw.pop("state", None)
        if state is not None:
            kw["state"] = state
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "values":
            return self.cget("values")
        if key == "state":
            return self.cget("state")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})


# ---------------------------------------------------------------------------
# checkbutton / radiobutton
# ---------------------------------------------------------------------------

class CompatCheckbutton(_Base, ctk.CTkCheckBox):
    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "activebackground", "activeforeground", "selectcolor",
                "disabledselectcolor", "indicatoron", "justify"):
            kw.pop(dead, None)
        kw.setdefault("fg_color", _parent_fg(master))
        kw.setdefault("checkmark_color", _c("accent_strong", "#6f52ee"))
        kw.setdefault("border_color", _c("border", "#222b3d"))
        kw.setdefault("hover_color", _c("bg", "#080b12"))
        kw.setdefault("text_color", _c("text", "#e8eef7"))
        kw.setdefault("checkbox_width", 18)
        kw.setdefault("checkbox_height", 18)
        kw.setdefault("font", _font(kw.pop("font", None), ("Segoe UI", 12)))
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "activebackground", "selectcolor", "indicatoron", "justify"):
            kw.pop(dead, None)
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "state":
            return self.cget("state")
        if key == "text":
            return self.cget("text")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})


class CompatRadiobutton(_Base, ctk.CTkRadioButton):
    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "activebackground", "activeforeground", "selectcolor",
                "indicatoron", "justify"):
            kw.pop(dead, None)
        kw.setdefault("fg_color", _parent_fg(master))
        kw.setdefault("border_color", _c("border", "#222b3d"))
        kw.setdefault("hover_color", _c("bg", "#080b12"))
        kw.setdefault("text_color", _c("text", "#e8eef7"))
        kw.setdefault("radiobutton_width", 18)
        kw.setdefault("radiobutton_height", 18)
        kw.setdefault("font", _font(kw.pop("font", None), ("Segoe UI", 12)))
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        kw.pop("style", None)
        for dead in _DEAD_WIDGET_KWARGS + (
                "activebackground", "selectcolor", "indicatoron", "justify"):
            kw.pop(dead, None)
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "text":
            return self.cget("text")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})


# ---------------------------------------------------------------------------
# progressbar (ttk value/maximum semantics over CTk 0..1)
# ---------------------------------------------------------------------------

class CompatProgressbar(_Base, ctk.CTkProgressBar):
    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        for dead in ("orient", "length", "takefocus", "cursor"):
            kw.pop(dead, None)
        mode = kw.pop("mode", "determinate")
        self._maximum = float(kw.pop("maximum", 1.0) or 1.0)
        initial = float(kw.pop("value", 0.0) or 0.0)
        kw.setdefault("progress_color", _c("accent_strong", "#6f52ee"))
        kw.setdefault("fg_color", _c("input", "#101623"))
        kw.setdefault("corner_radius", 6)
        kw.setdefault("height", 10)
        kw.pop("mode", None)
        super().__init__(master, **kw)
        if mode != "determinate":
            self._mode = mode
        self.set(max(0.0, min(1.0, initial / self._maximum)))

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            try:
                return super().configure(cnf)
            except Exception:
                return {}
        kw.pop("style", None)
        kw.pop("mode", None)
        kw.pop("orient", None)
        if "maximum" in kw:
            old = self._maximum
            self._maximum = float(kw.pop("maximum") or 1.0)
            if old:
                self.set(self.get() * old / self._maximum)
        if "value" in kw:
            value = float(kw.pop("value") or 0.0)
            self.set(max(0.0, min(1.0, value / self._maximum)))
        if not kw:
            return None
        return super().configure(**kw)

    def __getitem__(self, key):
        if key == "value":
            return self.get() * self._maximum
        if key == "maximum":
            return self._maximum
        if key == "mode":
            return getattr(self, "_mode", "determinate")
        return ""

    def __setitem__(self, key, value):
        self.configure(**{key: value})

    def step(self, amount=1.0):
        self.set(max(0.0, min(1.0, self.get() + amount / self._maximum)))

    def start(self, interval=None):
        pass  # indeterminate animation not used by the app

    def stop(self):
        pass


# ---------------------------------------------------------------------------
# Text + Treeview replacements (CTk has no equivalents)
# ---------------------------------------------------------------------------

class ThemedText(tk.Text):
    """Flat, palette-themed tk.Text for the activity/task logs."""

    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        for dead in ("relief", "bd", "borderwidth", "highlightthickness",
                     "highlightbackground", "highlightcolor", "cursor",
                     "insertbackground", "selectbackground", "selectforeground",
                     "setgrid", "autoseparators"):
            kw.pop(dead, None)
        kw.setdefault("bg", _c("input", "#101623"))
        kw.setdefault("fg", _c("text", "#e8eef7"))
        kw.setdefault("insertbackground", _c("text", "#e8eef7"))
        kw.setdefault("selectbackground", _c("accent_strong", "#6f52ee"))
        kw.setdefault("selectforeground", "#ffffff")
        kw.setdefault("relief", "flat")
        kw.setdefault("borderwidth", 0)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("padx", 10)
        kw.setdefault("pady", 8)
        kw.setdefault("wrap", "word")
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if cnf is not None and not kw:
            return super().configure(cnf)
        for dead in ("style", "relief", "bd", "highlightthickness",
                     "highlightbackground", "highlightcolor", "cursor"):
            kw.pop(dead, None)
        return super().configure(**kw)


class ThemedTree(ttk.Treeview):
    """ttk.Treeview restyled from the shared palette (flat rows, themed
    selection, borderless heading). Registers itself for theme rebuilds."""

    def __init__(self, master=None, **kw):
        kw.pop("style", None)
        kw.setdefault("show", "headings")
        super().__init__(master, **kw)
        _TREES.append(self)
        self.bind("<Destroy>", lambda _e: self._forget(), add="+")
        self.restyle()

    def _forget(self):
        try:
            _TREES.remove(self)
        except ValueError:
            pass

    def restyle(self):
        card = _c("card", "#11151f")
        style = ttk.Style(self)
        style.configure("Compat.Treeview", background=card, fieldbackground=card,
                        foreground=_c("text", "#e8eef7"), rowheight=34,
                        borderwidth=0, relief="flat")
        style.map("Compat.Treeview",
                  background=[("selected", _c("accent_strong", "#6f52ee"))],
                  foreground=[("selected", "#ffffff")])
        style.configure("Compat.Treeview.Heading", background=card,
                        foreground=_c("muted", "#7e89a6"), relief="flat",
                        borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("Compat.Treeview.Heading", background=[("active", card)])
        try:
            self.configure(style="Compat.Treeview")
        except Exception:
            pass


def _parent_fg(master, fallback=None):
    """Parent's resolved fg_color, for widgets that cannot be transparent."""
    try:
        value = master.cget("fg_color")
    except Exception:
        value = None
    if isinstance(value, str) and value.startswith("#"):
        return value
    return fallback or _c("bg", "#080b12")


def restyle_trees() -> None:
    for tree in list(_TREES):
        try:
            if tree.winfo_exists():
                tree.restyle()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

class _ModuleShim:
    """Namespace proxy: mapped names resolve to wrappers, the rest to the
    real module (StringVar, END, Style, ...). Patching the *importing
    module's* namespace (never the tkinter module itself) is essential:
    customtkinter internally calls ``tkinter.Frame.__init__`` and would
    recurse into the wrappers if the real module were mutated."""

    def __init__(self, real, mapping):
        self._real = real
        self._map = dict(mapping)

    def __getattr__(self, name):
        if name in self._map:
            return self._map[name]
        return getattr(self._real, name)


def install(module=None) -> None:
    """Rebind the tk/ttk widget names in the *importing module's* namespace
    onto the CTk-backed wrappers. Pass ``sys.modules[__name__]`` from the
    app module right after importing this package."""
    tk_map = {"Frame": CompatFrame, "Label": CompatLabel,
              "Button": CompatButton, "Entry": CompatEntry}
    ttk_map = {"Frame": CompatFrame, "Label": CompatLabel,
               "Button": CompatButton, "Entry": CompatEntry,
               "Combobox": CompatComboBox, "Checkbutton": CompatCheckbutton,
               "Radiobutton": CompatRadiobutton, "Progressbar": CompatProgressbar}
    if module is not None:
        module.tk = _ModuleShim(tk, tk_map)
        module.ttk = _ModuleShim(ttk, ttk_map)


def apply_window_scaling(root: tk.Tk) -> None:
    """CTk niceties for the root window (HiDPI awareness, dark default)."""
    try:
        ctk.set_appearance_mode("dark")
    except Exception:
        pass
