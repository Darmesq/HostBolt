"""
HostBolt - editor tip Notepad doar pentru fișierul hosts din Windows.

- Pornește automat ca Administrator (cere UAC dacă e nevoie).
- 🔒 Blochează: atribut read-only + permisiune NTFS "deny write" pentru Everyone,
  astfel încât nicio aplicație (ex. Adobe) să nu mai poată scrie în hosts.
- 🔓 Deblochează: scoate permisiunea de blocare ca să poți edita.
- 💾 Salvează: face întâi backup  hosts_AAAA-LL-ZZ_HH-MM-SS.bak  în același folder,
  apoi scrie fișierul și golește cache-ul DNS.
"""

import os
import re
import sys
import stat
import ctypes
import shutil
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

APP = "HostBolt"
VERSION = "1.0"
HOSTS = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                     "System32", "drivers", "etc", "hosts")
EVERYONE = "*S-1-1-0"          # SID-uri: merg și pe Windows în română
ADMINS = "*S-1-5-32-544"
NO_WINDOW = 0x08000000         # CREATE_NO_WINDOW


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


# ------------------------------------------------------------------ UI
def resource(name):
    """Fișier inclus în exe (PyInstaller) sau aflat lângă script."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.iconbitmap(default=resource("HostBolt.ico"))
        except tk.TclError:
            pass
        self.geometry("860x600")
        self.minsize(560, 360)
        self.encoding = "utf-8"
        self.locked = False

        self._build_ui()
        self.load()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        try:
            ttk.Style(self).theme_use("vista")
        except tk.TclError:
            pass

        # meniu ca la Notepad
        menu = tk.Menu(self)
        fm = tk.Menu(menu, tearoff=0)
        fm.add_command(label="Salvează", accelerator="Ctrl+S", command=self.save)
        fm.add_command(label="Reîncarcă", accelerator="F5", command=self.reload)
        fm.add_separator()
        fm.add_command(label="Deschide folderul etc", command=self.open_folder)
        fm.add_separator()
        fm.add_command(label="Ieșire", command=self.on_close)
        menu.add_cascade(label="Fișier", menu=fm)
        em = tk.Menu(menu, tearoff=0)
        em.add_command(label="Caută…", accelerator="Ctrl+F", command=self.show_find)
        em.add_command(label="Următorul", accelerator="F3", command=lambda: self.find_step(1))
        em.add_command(label="Anteriorul", accelerator="Shift+F3", command=lambda: self.find_step(-1))
        menu.add_cascade(label="Editare", menu=em)
        self.config(menu=menu)

        # bară de butoane
        bar = ttk.Frame(self, padding=(6, 6))
        bar.pack(fill="x")
        self.btn_lock = ttk.Button(bar, text="🔒  Închide (Lock)", command=self.do_lock)
        self.btn_lock.pack(side="left")
        self.btn_unlock = ttk.Button(bar, text="🔓  Deschide (Unlock)", command=self.do_unlock)
        self.btn_unlock.pack(side="left", padx=6)
        self.btn_save = ttk.Button(bar, text="💾  Salvează", command=self.save)
        self.btn_save.pack(side="left")
        ttk.Button(bar, text="🔍  Caută", command=self.show_find).pack(side="left", padx=6)
        self.state_lbl = tk.Label(bar, font=("Segoe UI", 10, "bold"), padx=10)
        self.state_lbl.pack(side="right")

        # bară de căutare (ascunsă până la Ctrl+F)
        self.findbar = ttk.Frame(self, padding=(6, 0, 6, 6))
        ttk.Label(self.findbar, text="Caută:").pack(side="left")
        self.find_var = tk.StringVar()
        self.find_entry = ttk.Entry(self.findbar, textvariable=self.find_var, width=40)
        self.find_entry.pack(side="left", padx=6)
        ttk.Button(self.findbar, text="◀", width=3, command=lambda: self.find_step(-1)).pack(side="left")
        ttk.Button(self.findbar, text="▶", width=3, command=lambda: self.find_step(1)).pack(side="left", padx=(2, 8))
        self.exact_var = tk.BooleanVar(value=False)
        self.case_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.findbar, text="Domeniu exact", variable=self.exact_var,
                        command=self.run_find).pack(side="left")
        ttk.Checkbutton(self.findbar, text="Aa", variable=self.case_var,
                        command=self.run_find).pack(side="left", padx=6)
        self.find_result = tk.Label(self.findbar, font=("Segoe UI", 9, "bold"))
        self.find_result.pack(side="left", padx=8)
        self.btn_add = ttk.Button(self.findbar, text="➕ Adaugă ca blocat", command=self.add_from_find)
        ttk.Button(self.findbar, text="✕", width=3, command=self.hide_find).pack(side="right")
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
        self.text = tk.Text(frame, wrap="none", undo=True, font=("Consolas", 11),
                            relief="flat", borderwidth=0, padx=6, pady=4)
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.text.tag_configure("match", background="#fff3a3")
        self.text.tag_configure("current", background="#ffb84d")
        self.text.tag_raise("current")

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
        self.text.bind("<<Modified>>", self._on_modified)
        for ev in ("<KeyRelease>", "<ButtonRelease-1>"):
            self.text.bind(ev, self._update_pos)

    # ---------- căutare
    def show_find(self):
        if not self.findbar.winfo_ismapped():
            self.findbar.pack(fill="x", before=self.text_frame)
        # textul selectat devine termenul de căutare
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
        """Găsește toate aparițiile și le colorează."""
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
            # domeniul ca element separat (nu ca parte din alt domeniu); ignoră liniile comentate
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
            self.find_result.config(fg="#1a7f37",
                                    text=f"✔ EXISTĂ – {len(self.matches)} rezultate pe {lines} linii")
            # sare la primul rezultat de după cursor
            cur = self.text.index("insert")
            self.match_idx = next((i for i, (a, _) in enumerate(self.matches)
                                   if self.text.compare(a, ">=", cur)), 0)
            self._show_current()
        else:
            self.find_result.config(fg="#c62828", text="✖ NU EXISTĂ în fișier")
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
            messagebox.showinfo(APP, "Fișierul este blocat. Apasă întâi „Deschide (Unlock)”.")
            return
        end_text = self.text.get("end-2c", "end-1c")
        prefix = "" if end_text in ("", "\n") else "\n"
        self.text.insert("end-1c", f"{prefix}0.0.0.0 {term}\n")
        self.text.see("end")
        self.status.set(f"Adăugat „0.0.0.0 {term}” la final – apasă Salvează ca să se aplice.")
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
        lock = "BLOCAT" if self.locked else "deblocat"
        self.title(f"{star}hosts — {APP} {VERSION} ({lock})")

    def _refresh_state(self):
        self.locked = is_locked()
        if self.locked:
            self.state_lbl.config(text="🔒 BLOCAT – nimeni nu poate scrie", fg="#1a7f37")
            self.text.config(state="disabled", bg="#f3f3f3")
            self.btn_lock.state(["disabled"])
            self.btn_unlock.state(["!disabled"])
            self.btn_save.state(["disabled"])
        else:
            self.state_lbl.config(text="🔓 DEBLOCAT – editabil", fg="#b35900")
            self.text.config(state="normal", bg="white")
            self.btn_lock.state(["!disabled"])
            self.btn_unlock.state(["disabled"])
            self.btn_save.state(["!disabled"])
        self._update_title()

    # ---------- acțiuni
    def load(self):
        try:
            content, self.encoding = read_hosts()
        except OSError as e:
            messagebox.showerror(APP, f"Nu pot citi hosts:\n{e}")
            content = ""
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content.replace("\r\n", "\n"))
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.status.set(HOSTS)
        self._refresh_state()

    def reload(self):
        if self._modified() and not messagebox.askyesno(
                APP, "Ai modificări nesalvate. Le pierzi și reîncarci fișierul?"):
            return
        self.load()

    def do_unlock(self):
        try:
            unlock()
            self.status.set("Deblocat. Poți edita fișierul.")
        except Exception as e:
            messagebox.showerror(APP, f"Deblocarea a eșuat:\n{e}")
        self._refresh_state()

    def do_lock(self):
        if self._modified():
            ans = messagebox.askyesnocancel(APP, "Ai modificări nesalvate. Le salvezi înainte de blocare?")
            if ans is None:
                return
            if ans and not self.save():
                return
            if not ans:
                self.load()
        try:
            lock()
            self.status.set("Blocat. Nicio aplicație nu mai poate modifica hosts.")
        except Exception as e:
            messagebox.showerror(APP, f"Blocarea a eșuat:\n{e}")
        self._refresh_state()

    def save(self):
        if self.locked:
            messagebox.showinfo(APP, "Fișierul este blocat. Apasă întâi „Deschide (Unlock)”.")
            return False
        content = self.text.get("1.0", "end-1c")
        try:
            bak = backup_hosts()
            enc = "utf-8" if self.encoding == "utf-8-sig" else self.encoding
            with open(HOSTS, "w", encoding=enc, newline="\r\n") as f:
                f.write(content)
            run(["ipconfig", "/flushdns"])
        except Exception as e:
            messagebox.showerror(APP, f"Salvarea a eșuat:\n{e}")
            return False
        self.text.edit_modified(False)
        self._update_title()
        self.status.set(f"Salvat. Backup: {os.path.basename(bak)}  •  cache DNS golit")
        return True

    def open_folder(self):
        os.startfile(os.path.dirname(HOSTS))

    def on_close(self):
        if self._modified():
            ans = messagebox.askyesnocancel(APP, "Salvezi modificările înainte de ieșire?")
            if ans is None:
                return
            if ans and not self.save():
                return
        if not self.locked and messagebox.askyesno(
                APP, "Fișierul hosts este DEBLOCAT.\nÎl blochezi înainte de ieșire?"):
            try:
                lock()
            except Exception as e:
                messagebox.showerror(APP, f"Blocarea a eșuat:\n{e}")
        self.destroy()


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("HostBolt rulează doar pe Windows.")
    if not is_admin():
        if not relaunch_as_admin():
            ctypes.windll.user32.MessageBoxW(None, "Aplicația are nevoie de drepturi de Administrator.", APP, 0x10)
        sys.exit(0)
    App().mainloop()
