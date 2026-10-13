# HostBolt

A lightweight Windows editor dedicated to the `hosts` file, with one-click locking to stop other programs from silently changing it.

**Author:** AlexS-/-DarmesQ  ·  **Version:** 1.0

[☕ Support HostBolt on Ko-fi](https://ko-fi.com/darmesq). HostBolt is free; if it helps you, a $3 coffee is appreciated.

---

Some installers and background services (for example, licensing or update agents) write their own entries into the `hosts` file. HostBolt lets you view and edit that file in a simple Notepad-style window, then lock it so those changes can't happen behind your back.

> **Note:** the user interface of version 1.0 is in Romanian.

## Features (v1.0)

### Editor
- **Hosts-only editor**: opens `C:\Windows\System32\drivers\etc\hosts` directly. There's no file browsing and no risk of editing the wrong file.
- **Notepad-style window** with undo, a line/column indicator and a status bar.
- **Runs as administrator automatically**: if started without admin rights, it requests elevation through UAC.

### Lock / Unlock
- **Lock** sets the file to read-only and adds an NTFS **deny write** permission for *Everyone*. No application can modify, delete or change the permissions of the hosts file while it's locked.
- **Unlock** removes the deny permission and the read-only attribute, so you can edit again.
- The current state (**LOCKED** / **UNLOCKED**) is always shown in the toolbar and in the window title. While the file is locked, the editor is read-only.
- **Reminder on exit**: if the file is unlocked when you close the app, HostBolt asks whether to lock it before exiting.

### Save
- **Automatic backup**: before every save, the previous version is copied to `hosts_YYYY-MM-DD_HH-MM-SS.bak` in the same `etc` folder.
- **DNS cache flush**: after saving, HostBolt runs `ipconfig /flushdns` so changes take effect immediately.
- Keeps the original file encoding and Windows line endings.

### Search
- **Live search bar** (`Ctrl+F`) that highlights all matches as you type and shows how many were found and on how many lines.
- **Navigation** between results with `F3` / `Shift+F3`, `Enter` / `Shift+Enter`, or the ◀ ▶ buttons.
- **Exact domain** option: matches the domain only as a whole entry (e.g. `adobe.com` won't match `test.adobe.com`) and ignores commented-out lines.
- **Case-sensitive** option (`Aa`).
- **Add as blocked**: if a searched domain isn't in the file, one click appends `0.0.0.0 domain` to the end of the file. You then save to apply it.

### Other
- **Reload** the file from disk (`F5`).
- **Open the `etc` folder** in Explorer from the File menu.
- Warns about unsaved changes before reloading, locking or exiting.

Version 1.0 has no settings window. Everything works out of the box.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+S` | Save (with backup) |
| `Ctrl+F` | Open search |
| `F3` / `Shift+F3` | Next / previous match |
| `Esc` | Close search bar |
| `F5` | Reload file |

## Requirements

- Windows 10 or 11
- Administrator rights
- To run from source: Python 3.x (uses only the standard library, including `tkinter`)

## Usage

### Run the compiled app
Download `HostBolt.exe` from the [Releases](../../releases) page and run it. Accept the administrator (UAC) prompt.

### Run from source
```bash
python HostBolt.py
```
The app requests administrator rights on its own if needed.

### Build the executable
Run the build script from the project folder:
```bash
build_hostbolt.bat
```
It packages `HostBolt.py` with PyInstaller into a standalone `.exe` that uses `HostBolt.ico` as its icon.

## Typical workflow

1. Open HostBolt.
2. Press `Ctrl+F` and search for a domain.
3. Click **Unlock** if the file is locked.
4. Edit the entries, or use **Add as blocked** for a domain that isn't there yet.
5. Click **Save**. A backup is created and the DNS cache is flushed automatically.
6. Click **Lock** to protect the file again.

## Restoring a backup

Backups are stored next to the hosts file in `C:\Windows\System32\drivers\etc\`. To restore one, unlock the file in HostBolt, copy the contents of the `.bak` file you want into the editor, and save.

## Project files

| File | Purpose |
|---|---|
| `HostBolt.py` | Application source code |
| `HostBolt.ico` | Application icon |
| `build_hostbolt.bat` | Builds the standalone Windows executable |

## Notes

- Some security software (including Windows Defender) monitors the hosts file and may warn you when HostBolt changes it. This is expected.
- While the file is locked, legitimate tools that need to modify it will also be blocked. Unlock it temporarily if needed.

## Disclaimer

HostBolt modifies a Windows system file and its permissions, and requires administrator rights. It is provided "as is", without warranty of any kind. Use it at your own risk. The author is not responsible for any damage, data loss, network problems or other issues caused by using this software. Always keep a backup of your hosts file before making changes.

## License

Released under the [MIT License](LICENSE).

## Author & support

Made by **AlexS-/-DarmesQ** · [github.com/Darmesq](https://github.com/Darmesq)

If HostBolt saves you some trouble, you can support its development with a coffee:

[☕ Support HostBolt on Ko-fi](https://ko-fi.com/darmesq)
