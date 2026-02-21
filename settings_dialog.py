import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import configparser

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")
STARTER_JSON = os.path.join(os.path.dirname(__file__), "starter.json")
DEFAULT_V8I = os.path.expandvars("%APPDATA%/1C/1CEStart/ibases.v8i")

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"v8i_paths": [DEFAULT_V8I] if os.path.exists(DEFAULT_V8I) else []}

def save_settings(data):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def parse_v8i_file(path):
    config = configparser.ConfigParser(strict=False)
    config.optionxform = str

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(path, "r", encoding=encoding) as f:
                config.read_file(f)
            break
        except Exception:
            continue
    else:
        raise RuntimeError(f"Не удалось прочитать {path} ни в utf-8-sig, ни в cp1251")

    bases = []
    for section in config.sections():
        entry = config[section]
        name = entry.get("Name", section)
        connect = entry.get("Connect", "")
        folder = entry.get("Folder", "")
        platform = entry.get("Version", entry.get("DefaultVersion", ""))
        username = entry.get("Usr", "")
        password = entry.get("Pwd", "")
        parameters = entry.get("App", "")
        interface = "Auto"

        if connect:
            bases.append({
                "name": name,
                "connect": connect,
                "folder": folder,
                "platform": platform,
                "username": username,
                "password": password,
                "parameters": parameters,
                "interface": interface,
                "auth_mode": "manual" if username else "auto",
                "auth_os": False,
                "auth_enterprise": {"username": username, "password": password},
                "auth_designer": {"username": "", "password": ""},
                "last_run": "",
                "size": ""
            })
    return bases

def open_settings_dialog(master):
    settings = load_settings()

    dialog = tk.Toplevel(master)
    dialog.title("Настройки CatStarter")
    dialog.geometry("600x400")
    dialog.grab_set()

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    frame_import = ttk.Frame(notebook)
    notebook.add(frame_import, text="Импорт баз")

    paths_var = tk.Variable(value=settings.get("v8i_paths", []))

    listbox = tk.Listbox(frame_import, listvariable=paths_var, height=8, selectmode="browse")
    listbox.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
    frame_import.rowconfigure(0, weight=1)
    frame_import.columnconfigure(1, weight=1)

    def add_path():
        path = filedialog.askopenfilename(title="Выберите .v8i файл", filetypes=[("v8i files", "*.v8i")])
        if path:
            current = list(paths_var.get())
            if path not in current:
                current.append(path)
                paths_var.set(current)

    def remove_path():
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            current = list(paths_var.get())
            del current[index]
            paths_var.set(current)

    def import_now():
        v8i_paths = list(paths_var.get())
        if not v8i_paths:
            messagebox.showinfo("Импорт", "Нет выбранных файлов .v8i")
            return

        if os.path.exists(STARTER_JSON):
            with open(STARTER_JSON, "r", encoding="utf-8") as f:
                starter = json.load(f)
        else:
            starter = {"favorites": [], "groups": []}

        existing_connects = set()

        def collect_existing_connects(groups):
            for g in groups:
                if g.get("type") == "base":
                    existing_connects.add(g.get("connect"))
                elif g.get("type") == "group":
                    collect_existing_connects(g.get("children", []))

        collect_existing_connects(starter.get("groups", []))

        def add_to_group_path(groups, folder_path, base):
            if not folder_path or folder_path.strip() in ["/", "\\"]:
                groups.append(base)
                return
            parts = folder_path.split("\\") if "\\" in folder_path else folder_path.split("/")
            current = groups
            for part in parts:
                match = next((g for g in current if g["type"] == "group" and g["name"] == part), None)
                if not match:
                    match = {"type": "group", "name": part, "children": []}
                    current.append(match)
                current = match["children"]
            current.append(base)

        added_count = 0
        for v8i_path in v8i_paths:
            if not os.path.exists(v8i_path):
                continue
            try:
                imported = parse_v8i_file(v8i_path)
                for b in imported:
                    if b["connect"] in existing_connects:
                        continue
                    base_entry = b
                    if not starter.get("groups"):
                        starter["groups"] = []
                    v8i_group = next((g for g in starter["groups"] if g.get("name") == "🗂 Импорт из .v8i"), None)
                    if not v8i_group:
                        v8i_group = {"type": "group", "name": "🗂 Импорт из .v8i", "children": []}
                        starter["groups"].append(v8i_group)
                    add_to_group_path(v8i_group["children"], b.get("folder", ""), base_entry)
                    existing_connects.add(b["connect"])
                    added_count += 1
            except Exception as e:
                print(f"[!] Ошибка при импорте {v8i_path}: {e}")

        with open(STARTER_JSON, "w", encoding="utf-8") as f:
            json.dump(starter, f, ensure_ascii=False, indent=4)

        messagebox.showinfo("Импорт завершён", f"Импортировано баз: {added_count}")

    ttk.Button(frame_import, text="Добавить", command=add_path).grid(row=1, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(frame_import, text="Удалить", command=remove_path).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
    ttk.Button(frame_import, text="Импортировать сейчас", command=import_now).grid(row=1, column=2, sticky="ew", padx=5, pady=5)

    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=(0, 10))

    def save_and_close():
        settings["v8i_paths"] = list(paths_var.get())
        save_settings(settings)
        dialog.destroy()

    ttk.Button(button_frame, text="Сохранить", command=save_and_close).pack(side="right")
    ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side="right", padx=(0, 5))
