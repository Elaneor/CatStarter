import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import copy
import json
import os
import sys
from v8i_utils import (
    normalize_path,
    parse_v8i_file,
    DEFAULT_V8I
)

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
STARTER_JSON = os.path.join(APP_DIR, "starter.json")
IMPORT_WARNINGS_PATH = os.path.join(APP_DIR, "import_warnings.txt")




def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["v8i_paths"] = [
            normalize_path(p)
            for p in data.get("v8i_paths", [])
        ]

        return data

    return {"v8i_paths": [normalize_path(DEFAULT_V8I)] if os.path.exists(DEFAULT_V8I) else []}
    
def save_settings(data):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# обновленная модель импорта баз

ROOT_GROUP_NAME = "Информационные базы"


def get_v8i_root_name(v8i_path):
    default_path = normalize_path(DEFAULT_V8I).lower()
    current_path = normalize_path(v8i_path).lower()

    if current_path == default_path:
        return ROOT_GROUP_NAME

    filename = os.path.basename(normalize_path(v8i_path))
    return f"Информационные базы из {filename}"


def make_base_entry(raw_base, source_v8i):
    username = raw_base.get("username", "")
    password = raw_base.get("password", "")

    return {
        "type": "base",
        "name": raw_base.get("name", ""),
        "id": raw_base.get("id", ""),
        "platform": raw_base.get("platform", ""),
        "version": raw_base.get("version", ""),
        "default_version": raw_base.get("default_version", ""),
        "external": raw_base.get("external", False),
        "app": raw_base.get("app", ""),
        "connect": raw_base.get("connect", ""),
        "parameters": raw_base.get("parameters", ""),
        "interface": raw_base.get("interface", "Auto"),
        "username": username,
        "password": password,
        "auth_mode": raw_base.get("auth_mode", "manual" if username else "auto"),
        "auth_os": raw_base.get("auth_os", False),
        "auth_enterprise": raw_base.get(
            "auth_enterprise",
            {"username": username, "password": password}
        ),
        "auth_designer": raw_base.get(
            "auth_designer",
            {"username": "", "password": ""}
        ),
        "last_run": raw_base.get("last_run", ""),
        "size": raw_base.get("size", ""),
        "source_v8i": normalize_path(source_v8i)
    }

def add_empty_group_to_group_path(groups, folder_path, group):
    folder_path = (folder_path or "").strip()

    if not folder_path or folder_path in ["/", "\\"]:
        current = groups
    else:
        parts = folder_path.replace("/", "\\").split("\\")
        current = groups

        for part in parts:
            part = part.strip()

            if not part:
                continue

            match = next(
                (
                    g for g in current
                    if g.get("type") == "group"
                    and g.get("name") == part
                ),
                None
            )

            if not match:
                match = {
                    "type": "group",
                    "id": f"v8i_group::{group.get('source_v8i', '')}::{part}",
                    "name": part,
                    "children": [],
                    "source_v8i": group.get("source_v8i", "")
                }
                current.append(match)

            current = match["children"]

    if not any(
        item.get("type") == "group"
        and item.get("name") == group.get("name")
        for item in current
    ):
        current.append(group)


def add_to_group_path(groups, folder_path, base):
    folder_path = (folder_path or "").strip()

    if not folder_path or folder_path in ["/", "\\"]:
        groups.append(base)
        return

    parts = folder_path.replace("/", "\\").split("\\")
    current = groups
    current_path = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        current_path.append(part)
        path_key = "\\".join(current_path)

        match = next(
            (
                g for g in current
                if g.get("type") == "group"
                and g.get("name") == part
            ),
            None
        )

        if not match:
            source_v8i = base.get("source_v8i", "")

            match = {
                "type": "group",
                "id": f"v8i_group::{source_v8i}::{path_key}",
                "name": part,
                "children": [],
                "source_v8i": source_v8i
            }
            current.append(match)

        current = match["children"]

    current.append(base)

# пользовательские поля для сохранения при импорте (обновлении из импорта)_
USER_FIELDS_TO_KEEP = [
    "username",
    "password",
    "auth_mode",
    "auth_os",
    "auth_enterprise",
    "auth_designer",
    "run_as_admin",
    "last_run",
    "size",
    "size_updated"
]


def collect_user_fields_index(nodes):
    result = {}

    def walk(items):
        for item in items:
            if item.get("type") == "group":
                walk(item.get("children", []))

            elif item.get("type") == "base":
                key = item.get("id") or item.get("connect")
                if key:
                    result[key] = {
                        field: item.get(field)
                        for field in USER_FIELDS_TO_KEEP
                        if field in item
                    }

    walk(nodes)
    return result


def restore_user_fields(base, user_fields_index):
    key = base.get("id") or base.get("connect")

    if key and key in user_fields_index:
        base.update(user_fields_index[key])



def import_v8i_into_starter(starter, v8i_paths):
    starter.setdefault("favorites", [])
    starter.setdefault("groups", [])
    user_fields_index = collect_user_fields_index(starter.get("groups", []))

    normalized_paths = [
        normalize_path(path)
        for path in v8i_paths
        if str(path).strip()
    ]

    root_names = {
        get_v8i_root_name(path)
        for path in normalized_paths
    }

    starter["groups"] = [
        group for group in starter.get("groups", [])
        if not (
            group.get("type") == "group"
            and group.get("name") in root_names
        )
    ]

    read_count = 0

    for v8i_path in normalized_paths:
        if not os.path.exists(v8i_path):
            continue

        root_group = {
            "type": "group",
            "id": f"v8i_root::{normalize_path(v8i_path)}",
            "name": get_v8i_root_name(v8i_path),
            "children": [],
            "source_v8i": normalize_path(v8i_path)
        }

        imported = parse_v8i_file(v8i_path)

        for raw_item in imported:
            if raw_item.get("type") == "group":
                group = {
                    "type": "group",
                    "id": f"v8i_group::{normalize_path(v8i_path)}::{raw_item.get('folder', '')}/{raw_item.get('name', '')}",
                    "name": raw_item.get("name", ""),
                    "children": [],
                    "source_v8i": normalize_path(v8i_path)
                }

                add_empty_group_to_group_path(
                    root_group["children"],
                    raw_item.get("folder", ""),
                    group
                )

                continue

            base = make_base_entry(raw_item, v8i_path)
            restore_user_fields(base, user_fields_index)

            add_to_group_path(
                root_group["children"],
                raw_item.get("folder", ""),
                base
            )

            read_count += 1

        starter["groups"].append(root_group)

    return read_count

def open_settings_dialog(master, on_close_callback=None):
    settings = load_settings()

    dialog = tk.Toplevel(master)
    dialog.title("Настройки CatStarter")
    dialog.geometry("600x400")
    dialog.grab_set()

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    frame_import = ttk.Frame(notebook)
    notebook.add(frame_import, text="Импорт баз")

    listbox = tk.Listbox(
        frame_import,
        height=8,
        selectmode="browse"
    )
    listbox.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

    for path in settings.get("v8i_paths", []):
        listbox.insert(tk.END, normalize_path(path))

    frame_import.rowconfigure(0, weight=1)
    frame_import.columnconfigure(1, weight=1)

    def get_paths_from_listbox():
        return [
            normalize_path(path)
            for path in listbox.get(0, tk.END)
            if str(path).strip()
        ]

    def add_path():
        path = filedialog.askopenfilename(
            title="Выберите .v8i файл",
            filetypes=[("v8i files", "*.v8i")]
        )

        if path:
            path = normalize_path(path)
            current = get_paths_from_listbox()
            if path not in current:
                listbox.insert(tk.END, path)

    def remove_path():
        selection = listbox.curselection()
        if selection:
            listbox.delete(selection[0])

    def import_now():
        v8i_paths = get_paths_from_listbox()
        if not v8i_paths:
            messagebox.showinfo("Импорт", "Нет выбранных файлов .v8i")
            return

        if os.path.exists(STARTER_JSON):
            with open(STARTER_JSON, "r", encoding="utf-8") as f:
                starter = json.load(f)
        else:
            starter = {"favorites": [], "groups": []}

        try:
            read_count = import_v8i_into_starter(starter, v8i_paths)
        except Exception as e:
            messagebox.showerror("Импорт", f"Не удалось импортировать список баз.\n{e}")
            return

        with open(STARTER_JSON, "w", encoding="utf-8") as f:
            json.dump(starter, f, ensure_ascii=False, indent=4)

        settings["v8i_paths"] = v8i_paths
        save_settings(settings)

        if on_close_callback:
            on_close_callback()
            
        messagebox.showinfo("Импорт завершен", f"Перечитано баз: {read_count}")
        dialog.destroy()

    ttk.Button(frame_import, text="Добавить", command=add_path).grid(row=1, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(frame_import, text="Удалить", command=remove_path).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
    ttk.Button(frame_import, text="Импортировать сейчас", command=import_now).grid(row=1, column=2, sticky="ew", padx=5, pady=5)

    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=(0, 10))

    def save_and_close():
        settings["v8i_paths"] = get_paths_from_listbox()
        save_settings(settings)

        if on_close_callback:
            on_close_callback()

        dialog.destroy()

    ttk.Button(button_frame, text="Сохранить", command=save_and_close).pack(side="right")
    ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side="right", padx=(0, 5))
