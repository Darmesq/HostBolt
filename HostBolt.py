"""
HostBolt - editor tip Notepad doar pentru fișierul hosts din Windows.

- Pornește automat ca Administrator (cere UAC dacă e nevoie).
- 🔒 Blochează: atribut read-only + permisiune NTFS "deny write" pentru Everyone,
  astfel încât nicio aplicație (ex. Adobe) să nu mai poată scrie în hosts.
- 🔓 Deblochează: scoate permisiunea de blocare ca să poți edita.
- 💾 Salvează: face întâi backup  hosts_AAAA-LL-ZZ_HH-MM-SS.bak  în același folder,
  apoi scrie fișierul și golește cache-ul DNS.
- 🔍 Căutare (Ctrl+F), cu verificare „domeniu exact”.
- ⚙ Setări: font editor, temă (Implicită / Luminoasă / Întunecată), limbă (RO / EN).
  Se salvează în settings.json lângă exe (sau în %APPDATA%\\HostBolt dacă folderul nu e scriibil).
"""

import os
import re
import sys
import json
import stat
import ctypes
import shutil
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

APP = "HostBolt"
VERSION = "1.1"
HOSTS = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                     "System32", "drivers", "etc", "hosts")
EVERYONE = "*S-1-1-0"          # SID-uri: merg și pe Windows în română
ADMINS = "*S-1-5-32-544"
NO_WINDOW = 0x08000000         # CREATE_NO_WINDOW

DEFAULT_SETTINGS = {"font_family": "Consolas", "font_size": 11, "theme": "default", "lang": "ro"}

# ------------------------------------------------------------------ texte RO / EN
STRINGS = {
    "ro": {
        "menu_file": "Fișier", "menu_edit": "Editare", "menu_settings": "Setări",
        "save": "Salvează", "reload": "Reîncarcă", "open_folder": "Deschide folderul etc",
        "exit": "Ieșire", "find_menu": "Caută…", "find_next": "Următorul", "find_prev": "Anteriorul",
        "settings_menu": "Preferințe…",
        "btn_lock": "🔒  Închide (Lock)", "btn_unlock": "🔓  Deschide (Unlock)",
        "btn_save": "💾  Salvează", "btn_find": "🔍  Caută", "btn_settings": "⚙",
        "find_label": "Caută:", "exact": "Domeniu exact", "add_blocked": "➕ Adaugă ca blocat",
        "found": "✔ EXISTĂ – {n} rezultate pe {lines} linii", "not_found": "✖ NU EXISTĂ în fișier",
        "state_locked": "🔒 BLOCAT – nimeni nu poate scrie", "state_unlocked": "🔓 DEBLOCAT – editabil",
        "title_locked": "BLOCAT", "title_unlocked": "deblocat",
        "locked_info": "Fișierul este blocat. Apasă întâi „Deschide (Unlock)”.",
        "added": "Adăugat „0.0.0.0 {d}” la final – apasă Salvează ca să se aplice.",
        "read_err": "Nu pot citi hosts:\n{e}",
        "reload_q": "Ai modificări nesalvate. Le pierzi și reîncarci fișierul?",
        "unlocked_st": "Deblocat. Poți edita fișierul.", "unlock_err": "Deblocarea a eșuat:\n{e}",
        "lock_save_q": "Ai modificări nesalvate. Le salvezi înainte de blocare?",
        "locked_st": "Blocat. Nicio aplicație nu mai poate modifica hosts.",
        "lock_err": "Blocarea a eșuat:\n{e}", "save_err": "Salvarea a eșuat:\n{e}",
        "saved_st": "Salvat. Backup: {b}  •  cache DNS golit",
        "exit_save_q": "Salvezi modificările înainte de ieșire?",
        "exit_lock_q": "Fișierul hosts este DEBLOCAT.\nÎl blochezi înainte de ieșire?",
        "need_admin": "Aplicația are nevoie de drepturi de Administrator.",
        # dialog setări
        "set_title": "Setări", "set_font": "Font editor", "set_family": "Font:", "set_size": "Mărime:",
        "set_mono": "Doar fonturi monospace", "set_preview": "Previzualizare:",
        "set_theme": "Temă", "theme_default": "Implicită (Windows)", "theme_light": "Luminoasă",
        "theme_dark": "Întunecată", "set_lang": "Limbă", "lang_ro": "Română", "lang_en": "English",
        "ok": "OK", "cancel": "Anulează", "apply": "Aplică", "reset": "Valori implicite",
    },
    "en": {
        "menu_file": "File", "menu_edit": "Edit", "menu_settings": "Settings",
        "save": "Save", "reload": "Reload", "open_folder": "Open etc folder",
        "exit": "Exit", "find_menu": "Find…", "find_next": "Find next", "find_prev": "Find previous",
        "settings_menu": "Preferences…",
        "btn_lock": "🔒  Lock", "btn_unlock": "🔓  Unlock",
        "btn_save": "💾  Save", "btn_find": "🔍  Find", "btn_settings": "⚙",
        "find_label": "Find:", "exact": "Exact domain", "add_blocked": "➕ Add as blocked",
        "found": "✔ EXISTS – {n} matches on {lines} lines", "not_found": "✖ NOT in the file",
        "state_locked": "🔒 LOCKED – nothing can write", "state_unlocked": "🔓 UNLOCKED – editable",
        "title_locked": "LOCKED", "title_unlocked": "unlocked",
        "locked_info": "The file is locked. Click “Unlock” first.",
        "added": "Added “0.0.0.0 {d}” at the end – click Save to apply it.",
        "read_err": "Cannot read hosts:\n{e}",
        "reload_q": "You have unsaved changes. Discard them and reload the file?",
        "unlocked_st": "Unlocked. You can edit the file.", "unlock_err": "Unlock failed:\n{e}",
        "lock_save_q": "You have unsaved changes. Save them before locking?",
        "locked_st": "Locked. No application can modify hosts.",
        "lock_err": "Lock failed:\n{e}", "save_err": "Save failed:\n{e}",
        "saved_st": "Saved. Backup: {b}  •  DNS cache flushed",
        "exit_save_q": "Save your changes before exiting?",
        "exit_lock_q": "The hosts file is UNLOCKED.\nLock it before exiting?",
        "need_admin": "This application requires Administrator rights.",
        "set_title": "Settings", "set_font": "Editor font", "set_family": "Font:", "set_size": "Size:",
        "set_mono": "Monospace fonts only", "set_preview": "Preview:",
        "set_theme": "Theme", "theme_default": "Default (Windows)", "theme_light": "Light",
        "theme_dark": "Dark", "set_lang": "Language", "lang_ro": "Română", "lang_en": "English",
        "ok": "OK", "cancel": "Cancel", "apply": "Apply", "reset": "Restore defaults",
    },
}

# ------------------------------------------------------------------ teme
THEMES = {
    "default": None,   # tema nativă Windows (vista)
    "light": {
        "bg": "#f5f6f8", "fg": "#1f2328", "muted": "#59636e",
        "text_bg": "#ffffff", "text_fg": "#1f2328", "locked_bg": "#eef0f3",
        "insert": "#1f2328", "sel_bg": "#b6d4fe", "sel_fg": "#1f2328",
        "entry_bg": "#ffffff", "btn_bg": "#e7eaee", "btn_active": "#d5dae1", "border": "#c9d1d9",
        "match": "#fff3a3", "current": "#ffb84d",
        "ok": "#1a7f37", "warn": "#b35900", "err": "#c62828",
    },
    "dark": {
        "bg": "#1e1f22", "fg": "#e6e6e6", "muted": "#9aa0a6",
        "text_bg": "#16171a", "text_fg": "#e6e6e6", "locked_bg": "#26272b",
        "insert": "#e6e6e6", "sel_bg": "#264f78", "sel_fg": "#ffffff",
        "entry_bg": "#2b2d31", "btn_bg": "#2f3136", "btn_active": "#3d4047", "border": "#45484f",
        "match": "#6b5a00", "current": "#b36b00",
        "ok": "#4ade80", "warn": "#fbbf24", "err": "#f87171",
    },
}
DEFAULT_COLORS = {"text_bg": "white", "text_fg": "black", "locked_bg": "#f3f3f3",
                  "insert": "black", "sel_bg": "#cce4ff", "sel_fg": "black",
                  "match": "#fff3a3", "current": "#ffb84d",
                  "ok": "#1a7f37", "warn": "#b35900", "err": "#c62828"}


# ------------------------------------------------------------------ admin
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, ""
    else:
        exe = sys.executable
        params = f'"{os.path.abspath(__file__)}"'
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return rc > 32


# ------------------------------------------------------------------ hosts
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW)
    out = (r.stdout or b"") + (r.stderr or b"")
    return r.returncode, out.decode("cp852", errors="replace")


def is_locked():
    _, out = run(["icacls", HOSTS])
    return "(DENY)" in out.upper()


def lock():
    # ordinea contează: atributul se pune ÎNAINTE de deny (deny blochează și atributele)
    os.chmod(HOSTS, stat.S_IREAD)
    run(["icacls", HOSTS, "/setowner", ADMINS])
    code, out = run(["icacls", HOSTS, "/deny", f"{EVERYONE}:(W,D,WDAC,WO)"])
    if code != 0:
        raise RuntimeError(out.strip())


def unlock():
    # ordinea inversă: întâi scoatem deny, apoi atributul read-only
    code, out = run(["icacls", HOSTS, "/remove:d", EVERYONE])
    if code != 0:
        raise RuntimeError(out.strip())
    os.chmod(HOSTS, stat.S_IREAD | stat.S_IWRITE)


def read_hosts():
    with open(HOSTS, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


def backup_hosts():
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dst = os.path.join(os.path.dirname(HOSTS), f"hosts_{stamp}.bak")
    shutil.copy2(HOSTS, dst)
    return dst


# ------------------------------------------------------------------ setări / resurse
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource(name):
    """Fișier inclus în exe (PyInstaller) sau aflat lângă script."""
    return os.path.join(getattr(sys, "_MEIPASS", app_dir()), name)


def settings_path():
    """Lângă exe (portabil); dacă folderul nu e scriibil -> %APPDATA%\\HostBolt."""
    local = os.path.join(app_dir(), "settings.json")
    try:
        with open(local, "a", encoding="utf-8"):
            pass
        return local
    except OSError:
        d = os.path.join(os.environ.get("APPDATA", app_dir()), APP)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "settings.json")


def load_settings():
    s = dict(DEFAULT_SETTINGS)
    try:
        with open(settings_path(), encoding="utf-8") as f:
            data = json.load(f)
        s.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    except (OSError, ValueError):
        pass
    if s["theme"] not in THEMES:
        s["theme"] = "default"
    if s["lang"] not in STRINGS:
        s["lang"] = "ro"
    return s


def save_settings(s):
    try:
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def set_dark_titlebar(win, dark):
    """Bară de titlu întunecată pe Windows 10 (1809+) / 11."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (nou / vechi)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4) == 0:
                break
        # forțează redesenarea barei de titlu
        w, h = win.winfo_width(), win.winfo_height()
        if w > 1:
            win.geometry(f"{w + 1}x{h}")
            win.geometry(f"{w}x{h}")
    except Exception:
        pass


# ------------------------------------------------------------------ fereastra principală
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.iconbitmap(default=resource("HostBolt.ico"))
        except tk.TclError:
            pass
        self.geometry("880x600")
        self.minsize(600, 360)
        self.encoding = "utf-8"
        self.locked = False
        self.settings = load_settings()
        self.style = ttk.Style(self)
        self.native_theme = "vista" if "vista" in self.style.theme_names() else self.style.theme_use()
        self.colors = dict(DEFAULT_COLORS)
        self.i18n = []          # (widget, cheie) pentru retraducere

        self._build_ui()
        self.apply_settings()
        self.load()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- utilitare
    def t(self, key, **kw):
        s = STRINGS[self.settings["lang"]].get(key) or STRINGS["ro"][key]
        return s.format(**kw) if kw else s

    def _tr(self, widget, key):
        self.i18n.append((widget, key))
        widget.config(text=self.t(key))
        return widget

    # ---------- interfață
    def _build_ui(self):
        # bară de butoane
        bar = ttk.Frame(self, padding=(6, 6))
        bar.pack(fill="x")
        self.btn_lock = self._tr(ttk.Button(bar, command=self.do_lock), "btn_lock")
        self.btn_lock.pack(side="left")
        self.btn_unlock = self._tr(ttk.Button(bar, command=self.do_unlock), "btn_unlock")
        self.btn_unlock.pack(side="left", padx=6)
        self.btn_save = self._tr(ttk.Button(bar, command=self.save), "btn_save")
        self.btn_save.pack(side="left")
        self._tr(ttk.Button(bar, command=self.show_find), "btn_find").pack(side="left", padx=6)
        self._tr(ttk.Button(bar, width=3, command=self.open_settings), "btn_settings").pack(side="left")
        self.state_lbl = tk.Label(bar, font=("Segoe UI", 10, "bold"), padx=10)
        self.state_lbl.pack(side="right")

        # bară de căutare (ascunsă până la Ctrl+F)
        self.findbar = ttk.Frame(self, padding=(6, 0, 6, 6))
        # butonul ✕ se împachetează primul, ca să nu fie împins afară când fereastra e îngustă
        ttk.Button(self.findbar, text="✕", width=3, command=self.hide_find).pack(side="right")
        self._tr(ttk.Label(self.findbar), "find_label").pack(side="left")
        self.find_var = tk.StringVar()
        self.find_entry = ttk.Entry(self.findbar, textvariable=self.find_var, width=28)
        self.find_entry.pack(side="left", padx=6)
        ttk.Button(self.findbar, text="◀", width=2, command=lambda: self.find_step(-1)).pack(side="left")
        ttk.Button(self.findbar, text="▶", width=2, command=lambda: self.find_step(1)).pack(side="left", padx=(2, 8))
        self.exact_var = tk.BooleanVar(value=False)
        self.case_var = tk.BooleanVar(value=False)
        self._tr(ttk.Checkbutton(self.findbar, variable=self.exact_var, command=self.run_find),
                 "exact").pack(side="left")
        ttk.Checkbutton(self.findbar, text="Aa", variable=self.case_var,
                        command=self.run_find).pack(side="left", padx=6)
        self.find_result = tk.Label(self.findbar, font=("Segoe UI", 9, "bold"))
        self.find_result.pack(side="left", padx=8)
        self.btn_add = self._tr(ttk.Button(self.findbar, command=self.add_from_find), "add_blocked")
        self.find_var.trace_add("write", lambda *a: self.run_find())
        self.find_entry.bind("<Return>", lambda e: self.find_step(1))
        self.find_entry.bind("<Shift-Return>", lambda e: self.find_step(-1))
        self.find_entry.bind("<Escape>", lambda e: self.hide_find())
        self.matches = []
        self.match_idx = -1

        # zona de text
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)
        self.text_frame = frame
        self.editor_font = tkfont.Font(family="Consolas", size=11)
        self.text = tk.Text(frame, wrap="none", undo=True, font=self.editor_font,
                            relief="flat", borderwidth=0, padx=6, pady=4, highlightthickness=0)
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # bară de stare
        self.status = tk.StringVar()
        self.pos = tk.StringVar(value="Ln 1, Col 1")
        sb = ttk.Frame(self, padding=(6, 2))
        sb.pack(fill="x")
        ttk.Label(sb, textvariable=self.status).pack(side="left")
        ttk.Label(sb, textvariable=self.pos).pack(side="right")

        self.bind_all("<Control-s>", lambda e: self.save())
        self.bind_all("<F5>", lambda e: self.reload())
        self.bind_all("<Control-f>", lambda e: (self.show_find(), "break")[1])
        self.bind_all("<F3>", lambda e: self.find_step(1))
        self.bind_all("<Shift-F3>", lambda e: self.find_step(-1))
        self.bind_all("<Control-comma>", lambda e: self.open_settings())
        self.text.bind("<<Modified>>", self._on_modified)
        for ev in ("<KeyRelease>", "<ButtonRelease-1>"):
            self.text.bind(ev, self._update_pos)

    def _build_menu(self):
        menu = tk.Menu(self)
        fm = tk.Menu(menu, tearoff=0)
        fm.add_command(label=self.t("save"), accelerator="Ctrl+S", command=self.save)
        fm.add_command(label=self.t("reload"), accelerator="F5", command=self.reload)
        fm.add_separator()
        fm.add_command(label=self.t("open_folder"), command=self.open_folder)
        fm.add_separator()
        fm.add_command(label=self.t("exit"), command=self.on_close)
        menu.add_cascade(label=self.t("menu_file"), menu=fm)
        em = tk.Menu(menu, tearoff=0)
        em.add_command(label=self.t("find_menu"), accelerator="Ctrl+F", command=self.show_find)
        em.add_command(label=self.t("find_next"), accelerator="F3", command=lambda: self.find_step(1))
        em.add_command(label=self.t("find_prev"), accelerator="Shift+F3", command=lambda: self.find_step(-1))
        menu.add_cascade(label=self.t("menu_edit"), menu=em)
        sm = tk.Menu(menu, tearoff=0)
        sm.add_command(label=self.t("settings_menu"), accelerator="Ctrl+,", command=self.open_settings)
        sm.add_separator()
        # comutare rapidă temă / limbă direct din meniu
        self.menu_theme = tk.StringVar(value=self.settings["theme"])
        self.menu_lang = tk.StringVar(value=self.settings["lang"])
        for key in ("default", "light", "dark"):
            sm.add_radiobutton(label=self.t(f"theme_{key}"), variable=self.menu_theme, value=key,
                               command=lambda: self._quick_set("theme", self.menu_theme.get()))
        sm.add_separator()
        for key in ("ro", "en"):
            sm.add_radiobutton(label=self.t(f"lang_{key}"), variable=self.menu_lang, value=key,
                               command=lambda: self._quick_set("lang", self.menu_lang.get()))
        menu.add_cascade(label=self.t("menu_settings"), menu=sm)
        self.config(menu=menu)

    def _quick_set(self, key, value):
        self.settings[key] = value
        save_settings(self.settings)
        self.apply_settings()

    # ---------- aplicare setări
    def apply_settings(self):
        s = self.settings
        # font editor
        self.editor_font.configure(family=s["font_family"], size=int(s["font_size"]))
        # temă
        pal = THEMES[s["theme"]]
        if pal is None:
            self.style.theme_use(self.native_theme)
            self.colors = dict(DEFAULT_COLORS)
            sys_bg = self.style.lookup("TFrame", "background") or "SystemButtonFace"
            self.colors["bg"] = sys_bg
            self.configure(bg=sys_bg)
            self.option_clear()
        else:
            self._apply_palette(pal)
        self.text.configure(fg=self.colors["text_fg"], insertbackground=self.colors["insert"],
                            selectbackground=self.colors["sel_bg"], selectforeground=self.colors["sel_fg"])
        self.text.tag_configure("match", background=self.colors["match"])
        self.text.tag_configure("current", background=self.colors["current"])
        self.text.tag_raise("current")
        for lbl in (self.state_lbl, self.find_result):
            lbl.configure(bg=self.colors["bg"])
        set_dark_titlebar(self, s["theme"] == "dark")
        # limbă
        for widget, key in self.i18n:
            widget.config(text=self.t(key))
        self._build_menu()
        if self.findbar.winfo_ismapped():
            self.run_find()
        self._refresh_state(check=False)

    def _apply_palette(self, p):
        self.colors = dict(p)
        st = self.style
        st.theme_use("clam")
        st.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["entry_bg"],
                     bordercolor=p["border"], lightcolor=p["bg"], darkcolor=p["bg"],
                     troughcolor=p["bg"], focuscolor=p["sel_bg"], insertcolor=p["insert"],
                     selectbackground=p["sel_bg"], selectforeground=p["sel_fg"])
        st.configure("TFrame", background=p["bg"])
        st.configure("TLabel", background=p["bg"], foreground=p["fg"])
        st.configure("TLabelframe", background=p["bg"], bordercolor=p["border"])
        st.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"])
        st.configure("TButton", background=p["btn_bg"], foreground=p["fg"], padding=(10, 4),
                     bordercolor=p["border"], lightcolor=p["btn_bg"], darkcolor=p["btn_bg"])
        st.map("TButton",
               background=[("disabled", p["bg"]), ("pressed", p["btn_active"]), ("active", p["btn_active"])],
               foreground=[("disabled", p["muted"])])
        for w in ("TCheckbutton", "TRadiobutton"):
            st.configure(w, background=p["bg"], foreground=p["fg"], indicatorbackground=p["entry_bg"],
                         indicatorforeground=p["fg"])
            st.map(w, background=[("active", p["bg"])], indicatorbackground=[("selected", p["sel_bg"])])
        st.configure("TEntry", fieldbackground=p["entry_bg"], foreground=p["fg"], insertcolor=p["insert"])
        st.configure("TCombobox", fieldbackground=p["entry_bg"], foreground=p["fg"],
                     background=p["btn_bg"], arrowcolor=p["fg"])
        st.map("TCombobox", fieldbackground=[("readonly", p["entry_bg"])],
               foreground=[("readonly", p["fg"])], selectbackground=[("readonly", p["entry_bg"])],
               selectforeground=[("readonly", p["fg"])])
        st.configure("TSpinbox", fieldbackground=p["entry_bg"], foreground=p["fg"],
                     background=p["btn_bg"], arrowcolor=p["fg"])
        st.configure("Vertical.TScrollbar", background=p["btn_bg"], troughcolor=p["bg"],
                     arrowcolor=p["fg"], bordercolor=p["bg"], lightcolor=p["btn_bg"],
                     darkcolor=p["btn_bg"], gripcount=0)
        st.configure("Horizontal.TScrollbar", background=p["btn_bg"], troughcolor=p["bg"],
                     arrowcolor=p["fg"], bordercolor=p["bg"], lightcolor=p["btn_bg"],
                     darkcolor=p["btn_bg"], gripcount=0)
        self.configure(bg=p["bg"])
        # lista derulantă a combobox-urilor
        self.option_add("*TCombobox*Listbox.background", p["entry_bg"])
        self.option_add("*TCombobox*Listbox.foreground", p["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", p["sel_bg"])
        self.option_add("*TCombobox*Listbox.selectForeground", p["sel_fg"])

    # ---------- dialog setări
    def open_settings(self):
        SettingsDialog(self)

    # ---------- căutare
    def show_find(self):
        if not self.findbar.winfo_ismapped():
            self.findbar.pack(fill="x", before=self.text_frame)
        try:
            sel = self.text.get("sel.first", "sel.last").strip()
            if sel and "\n" not in sel:
                self.find_var.set(sel)
        except tk.TclError:
            pass
        self.find_entry.focus_set()
        self.find_entry.select_range(0, "end")
        self.run_find()

    def hide_find(self):
        self.findbar.pack_forget()
        self.text.tag_remove("match", "1.0", "end")
        self.text.tag_remove("current", "1.0", "end")
        self.text.focus_set()

    def run_find(self):
        self.text.tag_remove("match", "1.0", "end")
        self.text.tag_remove("current", "1.0", "end")
        self.matches, self.match_idx = [], -1
        self.btn_add.pack_forget()
        term = self.find_var.get().strip()
        if not term:
            self.find_result.config(text="")
            return
        flags = 0 if self.case_var.get() else re.IGNORECASE
        if self.exact_var.get():
            pat = re.compile(r"(?<![\w.\-])" + re.escape(term.rstrip(".")) + r"\.?(?![\w.\-])", flags)
        else:
            pat = re.compile(re.escape(term), flags)
        content = self.text.get("1.0", "end-1c")
        for ln, line in enumerate(content.split("\n"), start=1):
            for m in pat.finditer(line):
                if self.exact_var.get() and "#" in line[:m.start()]:
                    continue
                a, b = f"{ln}.{m.start()}", f"{ln}.{m.end()}"
                self.text.tag_add("match", a, b)
                self.matches.append((a, b))
        if self.matches:
            lines = len({a.split(".")[0] for a, _ in self.matches})
            self.find_result.config(fg=self.colors["ok"], text=self.t("found", n=len(self.matches), lines=lines))
            cur = self.text.index("insert")
            self.match_idx = next((i for i, (a, _) in enumerate(self.matches)
                                   if self.text.compare(a, ">=", cur)), 0)
            self._show_current()
        else:
            self.find_result.config(fg=self.colors["err"], text=self.t("not_found"))
            if self._looks_like_domain(term):
                self.btn_add.pack(side="left")

    def find_step(self, direction):
        if not self.findbar.winfo_ismapped():
            self.show_find()
            return
        if not self.matches:
            self.run_find()
            return
        self.match_idx = (self.match_idx + direction) % len(self.matches)
        self._show_current()

    def _show_current(self):
        self.text.tag_remove("current", "1.0", "end")
        a, b = self.matches[self.match_idx]
        self.text.tag_add("current", a, b)
        self.text.mark_set("insert", a)
        self.text.see(a)
        self._update_pos()
        base = self.find_result.cget("text").split("  (")[0]
        self.find_result.config(text=f"{base}  ({self.match_idx + 1}/{len(self.matches)})")

    @staticmethod
    def _looks_like_domain(term):
        return bool(re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9\-]*[A-Za-z0-9])?(\.[A-Za-z0-9\-]+)+\.?", term))

    def add_from_find(self):
        term = self.find_var.get().strip().rstrip(".").lower()
        if self.locked:
            messagebox.showinfo(APP, self.t("locked_info"))
            return
        end_text = self.text.get("end-2c", "end-1c")
        prefix = "" if end_text in ("", "\n") else "\n"
        self.text.insert("end-1c", f"{prefix}0.0.0.0 {term}\n")
        self.text.see("end")
        self.status.set(self.t("added", d=term))
        self.run_find()

    # ---------- stare
    def _on_modified(self, _e=None):
        self._update_title()

    def _update_pos(self, _e=None):
        line, col = self.text.index("insert").split(".")
        self.pos.set(f"Ln {line}, Col {int(col) + 1}")

    def _modified(self):
        return bool(self.text.edit_modified())

    def _update_title(self):
        star = "*" if self._modified() else ""
        lock_txt = self.t("title_locked") if self.locked else self.t("title_unlocked")
        self.title(f"{star}hosts — {APP} {VERSION} ({lock_txt})")
        
    def _refresh_state(self, check=True):
        if check:
            self.locked = is_locked()
        if self.locked:
            self.state_lbl.config(text=self.t("state_locked"), fg=self.colors["ok"])
            self.text.config(state="disabled", bg=self.colors["locked_bg"])
            self.btn_lock.state(["disabled"])
            self.btn_unlock.state(["!disabled"])
            self.btn_save.state(["disabled"])
        else:
            self.state_lbl.config(text=self.t("state_unlocked"), fg=self.colors["warn"])
            self.text.config(state="normal", bg=self.colors["text_bg"])
            self.btn_lock.state(["!disabled"])
            self.btn_unlock.state(["disabled"])
            self.btn_save.state(["!disabled"])
        self._update_title()

    # ---------- acțiuni
    def load(self):
        try:
            content, self.encoding = read_hosts()
        except OSError as e:
            messagebox.showerror(APP, self.t("read_err", e=e))
            content = ""
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content.replace("\r\n", "\n"))
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.status.set(HOSTS)
        self._refresh_state()

    def reload(self):
        if self._modified() and not messagebox.askyesno(APP, self.t("reload_q")):
            return
        self.load()

    def do_unlock(self):
        try:
            unlock()
            self.status.set(self.t("unlocked_st"))
        except Exception as e:
            messagebox.showerror(APP, self.t("unlock_err", e=e))
        self._refresh_state()

    def do_lock(self):
        if self._modified():
            ans = messagebox.askyesnocancel(APP, self.t("lock_save_q"))
            if ans is None:
                return
            if ans and not self.save():
                return
            if not ans:
                self.load()
        try:
            lock()
            self.status.set(self.t("locked_st"))
        except Exception as e:
            messagebox.showerror(APP, self.t("lock_err", e=e))
        self._refresh_state()

    def save(self):
        if self.locked:
            messagebox.showinfo(APP, self.t("locked_info"))
            return False
        content = self.text.get("1.0", "end-1c")
        try:
            bak = backup_hosts()
            enc = "utf-8" if self.encoding == "utf-8-sig" else self.encoding
            with open(HOSTS, "w", encoding=enc, newline="\r\n") as f:
                f.write(content)
            run(["ipconfig", "/flushdns"])
        except Exception as e:
            messagebox.showerror(APP, self.t("save_err", e=e))
            return False
        self.text.edit_modified(False)
        self._update_title()
        self.status.set(self.t("saved_st", b=os.path.basename(bak)))
        return True

    def open_folder(self):
        os.startfile(os.path.dirname(HOSTS))

    def on_close(self):
        if self._modified():
            ans = messagebox.askyesnocancel(APP, self.t("exit_save_q"))
            if ans is None:
                return
            if ans and not self.save():
                return
        if not self.locked and messagebox.askyesno(APP, self.t("exit_lock_q")):
            try:
                lock()
            except Exception as e:
                messagebox.showerror(APP, self.t("lock_err", e=e))
        self.destroy()


# ------------------------------------------------------------------ dialog Setări
class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.original = dict(app.settings)
        self.title(app.t("set_title"))
        self.resizable(False, False)
        self.transient(app)
        self.configure(bg=app.colors.get("bg", "SystemButtonFace"))

        s = app.settings
        self.family = tk.StringVar(value=s["font_family"])
        self.size = tk.IntVar(value=int(s["font_size"]))
        self.theme = tk.StringVar(value=s["theme"])
        self.lang = tk.StringVar(value=s["lang"])
        self.mono_only = tk.BooleanVar(value=True)
        self._all_fonts = sorted({f for f in tkfont.families(self) if not f.startswith("@")}, key=str.lower)
        self._mono_fonts = None

        self._build()
        set_dark_titlebar(self, s["theme"] == "dark")
        self.grab_set()
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Return>", lambda e: self.ok())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        # centrat peste fereastra principală
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _build(self):
        t = self.app.t
        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)

        # --- font
        ff = ttk.LabelFrame(body, text=t("set_font"), padding=10)
        ff.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(ff, text=t("set_family")).grid(row=0, column=0, sticky="w")
        self.cb_font = ttk.Combobox(ff, textvariable=self.family, width=30, state="readonly")
        self.cb_font.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(ff, text=t("set_size")).grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Spinbox(ff, from_=7, to=36, textvariable=self.size, width=5,
                    command=self._preview).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Checkbutton(ff, text=t("set_mono"), variable=self.mono_only,
                        command=self._fill_fonts).grid(row=1, column=1, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(ff, text=t("set_preview")).grid(row=2, column=0, sticky="nw", pady=(10, 0))
        c = self.app.colors
        self.preview_font = tkfont.Font(family=self.family.get(), size=self.size.get())
        self.preview = tk.Label(ff, text="0.0.0.0  example.adobe.io\n127.0.0.1  localhost  # 0Oo 1lI",
                                font=self.preview_font, justify="left", anchor="w", padx=8, pady=6,
                                bg=c["text_bg"], fg=c["text_fg"], relief="flat", width=36)
        self.preview.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(10, 0), padx=6)
        self.cb_font.bind("<<ComboboxSelected>>", lambda e: self._preview())
        self.size.trace_add("write", lambda *a: self._preview())
        self._fill_fonts()

        # --- temă
        tf = ttk.LabelFrame(body, text=t("set_theme"), padding=10)
        tf.grid(row=1, column=0, sticky="nsew", pady=(10, 0), padx=(0, 5))
        for key in ("default", "light", "dark"):
            ttk.Radiobutton(tf, text=t(f"theme_{key}"), value=key, variable=self.theme
                            ).pack(anchor="w", pady=1)

        # --- limbă
        lf = ttk.LabelFrame(body, text=t("set_lang"), padding=10)
        lf.grid(row=1, column=1, sticky="nsew", pady=(10, 0), padx=(5, 0))
        for key in ("ro", "en"):
            ttk.Radiobutton(lf, text=t(f"lang_{key}"), value=key, variable=self.lang
                            ).pack(anchor="w", pady=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # --- butoane
        bb = ttk.Frame(body)
        bb.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(bb, text=t("reset"), command=self.reset).pack(side="left")
        ttk.Button(bb, text=t("cancel"), command=self.cancel).pack(side="right")
        ttk.Button(bb, text=t("apply"), command=self.apply).pack(side="right", padx=6)
        ttk.Button(bb, text=t("ok"), command=self.ok).pack(side="right")

    def _fill_fonts(self):
        if self.mono_only.get():
            if self._mono_fonts is None:
                self._mono_fonts = []
                for f in self._all_fonts:
                    try:
                        if tkfont.Font(family=f, size=10).metrics("fixed"):
                            self._mono_fonts.append(f)
                    except tk.TclError:
                        pass
            fonts = self._mono_fonts
        else:
            fonts = self._all_fonts
        cur = self.family.get()
        if cur not in fonts:
            fonts = [cur] + fonts
        self.cb_font["values"] = fonts
        self.cb_font["height"] = 15

    def _preview(self):
        try:
            self.preview_font.configure(family=self.family.get(), size=int(self.size.get()))
        except (tk.TclError, ValueError):
            pass

    def _collect(self):
        try:
            size = max(7, min(36, int(self.size.get())))
        except (tk.TclError, ValueError):
            size = DEFAULT_SETTINGS["font_size"]
        return {"font_family": self.family.get(), "font_size": size,
                "theme": self.theme.get(), "lang": self.lang.get()}

    def apply(self):
        new = self._collect()
        lang_changed = new["lang"] != self.app.settings["lang"]
        theme_changed = new["theme"] != self.app.settings["theme"]
        self.app.settings.update(new)
        save_settings(self.app.settings)
        self.app.apply_settings()
        if lang_changed or theme_changed:
            # redeschide dialogul în noua limbă / temă
            self.grab_release()
            self.destroy()
            d = SettingsDialog(self.app)
            d.original = self.original
            return d
        return self

    def ok(self):
        dlg = self.apply()
        dlg.grab_release()
        dlg.destroy()

    def cancel(self):
        if self.app.settings != self.original:
            self.app.settings.update(self.original)
            save_settings(self.app.settings)
            self.app.apply_settings()
        self.grab_release()
        self.destroy()

    def reset(self):
        self.family.set(DEFAULT_SETTINGS["font_family"])
        self.size.set(DEFAULT_SETTINGS["font_size"])
        self.theme.set(DEFAULT_SETTINGS["theme"])
        self.lang.set(DEFAULT_SETTINGS["lang"])
        self._fill_fonts()
        self._preview()


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("HostBolt runs on Windows only / rulează doar pe Windows.")
    if not is_admin():
        if not relaunch_as_admin():
            lang = load_settings()["lang"]
            ctypes.windll.user32.MessageBoxW(None, STRINGS[lang]["need_admin"], APP, 0x10)
        sys.exit(0)
    App().mainloop()
