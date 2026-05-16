import ctypes
import datetime
import json
import tkinter as tk
from tkinter import ttk, messagebox
import os
import pyperclip
import subprocess
import sys
import uuid
import webbrowser
from PIL import Image, ImageTk
from edit_dialog import (
    open_register_dialog,
    open_properties_dialog,
    center_window
)
from settings_dialog import open_settings_dialog
from command_dialog import open_command_dialog

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None

        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tooltip:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20

        self.tooltip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=2
        )
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = APP_DIR
    
def load_icon(name, size=(18, 18)):
    path = os.path.join(RESOURCE_DIR, "assets", "icons", name)
    img = Image.open(path).resize(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img)

STARTER_JSON = os.path.join(APP_DIR, "starter.json")
COMMANDS_JSON = os.path.join(APP_DIR, "commands.json")

root = tk.Tk()

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CatStarter.App")
except Exception:
    pass

root.title("Cat Starter")
icon_path = os.path.join(RESOURCE_DIR, "assets", "cat.ico")

if os.path.exists(icon_path):
    root.iconbitmap(icon_path)

root.geometry("900x600")

# Правая часть — панель запуска и Син
frame_right_container = tk.Frame(root, width=240)
frame_right_container.pack(side="right", fill="y")

frame_right = ttk.Frame(frame_right_container, padding=10)
frame_right.pack(fill="y", expand=True)

# Левая часть — дерево баз
frame_left = ttk.Frame(root, padding=10)
frame_left.pack(side="left", fill="both", expand=True)

# Панель поиска + кнопки
toolbar = ttk.Frame(frame_left)
toolbar.pack(side="top", fill="x", pady=(0, 5))

icon_create = load_icon("add.png")
icon_copy = load_icon("copy.png")
icon_group = load_icon("folder.png")
icon_settings = load_icon("settings.png")
icon_delete = load_icon("delete.png")
icon_version = load_icon("version.png")

search_var = tk.StringVar()
search_entry = ttk.Entry(
    toolbar,
    textvariable=search_var,
    width=24
)

search_entry.pack(side="left", padx=(0, 5))
SEARCH_PLACEHOLDER = "🔍 Ctrl+F"
search_var.set(SEARCH_PLACEHOLDER)

version_filter_var = tk.StringVar(value="")
filter_button_text = tk.StringVar(value="8.x")

def clear_search_placeholder(event=None):
    if search_var.get() == SEARCH_PLACEHOLDER:
        search_var.set("")

search_entry.bind("<FocusIn>", clear_search_placeholder)

# добавление группы
def create_group():
    dialog = tk.Toplevel(root)
    dialog.title("Создать группу")
    dialog.grab_set()
    dialog.resizable(False, False)

    ttk.Label(dialog, text="Название группы:").pack(padx=12, pady=(12, 4), anchor="w")

    name_var = tk.StringVar()
    entry = ttk.Entry(dialog, textvariable=name_var, width=35)
    entry.pack(padx=12, pady=(0, 8))
    entry.focus_set()

    def save():
        name = name_var.get().strip()
        if not name:
            messagebox.showinfo("Создать группу", "Введите название группы.")
            return

        new_group = {
            "type": "group",
            "name": name,
            "children": []
        }

        selected = tree.focus()
        if selected in tree_nodes and tree_nodes[selected].get("type") == "group":
            tree_nodes[selected].setdefault("children", []).append(new_group)
        elif starter.get("groups"):
            starter["groups"][0].setdefault("children", []).append(new_group)
        else:
            starter["groups"] = [{
                "type": "group",
                "name": "Информационные базы",
                "children": [new_group]
            }]

        save_json(starter)
        populate_tree()
        dialog.destroy()

    ttk.Button(dialog, text="Создать", command=save).pack(pady=(0, 12))

    entry.bind("<Return>", lambda e: save())

btn_create = ttk.Button(
    toolbar,
    image=icon_create,
    width=3,
    command=lambda: open_register_dialog(root, on_register_save)
)

ToolTip(btn_create, "Создать базу")

btn_filter = ttk.Button(
    toolbar,
    textvariable=filter_button_text,
    width=4,
    command=lambda: open_platform_filter_dialog()
)

ToolTip(btn_filter, "Отбор по версии платформы")

btn_group = ttk.Button(
    toolbar, 
    text="Создать группу", 
    command=create_group)
ToolTip(btn_group, "Создать группу")

btn_create.pack(side="left", padx=2)
btn_filter.pack(side="left", padx=2)
btn_group.pack(side="left", padx=2)

btn_settings = ttk.Button(
    toolbar,
    image=icon_settings,
    width=3,
    command=lambda: open_settings_dialog(root, reload_data)
)
ToolTip(btn_settings, "Настройки")

btn_settings.pack(side="left", padx=2)

# Генерация окна с закладками "Базы", "История", "Команды"
main_notebook = ttk.Notebook(frame_left)
main_notebook.pack(fill="both", expand=True)

bases_tab = ttk.Frame(main_notebook)
history_tab = ttk.Frame(main_notebook)
commands_tab = ttk.Frame(main_notebook)

main_notebook.add(bases_tab, text="1С:Предприятие 8")
main_notebook.add(history_tab, text="История")
main_notebook.add(commands_tab, text="Команды")

# Дерево баз
columns = ("platform", "last_run", "size")
tree = ttk.Treeview(
    bases_tab,
    columns=columns,
    show="tree headings",
    selectmode="extended"
)

tree.heading("#0", text="Наименование")
tree.heading("platform", text="Платформа")
tree.heading("last_run", text="Дата")
tree.heading("size", text="Размер")
tree.pack(fill="both", expand=True)

# Панель инструментов для команд
commands_toolbar = ttk.Frame(commands_tab)
commands_toolbar.pack(fill="x", pady=(0, 5))

btn_command_create = ttk.Button(
    commands_toolbar,
    text="Создать команду",
    command=lambda: create_command()
)
btn_command_create.pack(side="left", padx=2)

btn_command_group = ttk.Button(
    commands_toolbar,
    text="Создать группу"
)
btn_command_group.pack(side="left", padx=2)

btn_command_properties = ttk.Button(
    commands_toolbar,
    text="Свойства",
    command=lambda: open_selected_command_properties()
)
btn_command_properties.pack(side="left", padx=2)

btn_command_delete = ttk.Button(
    commands_toolbar,
    text="Удалить"
)
btn_command_delete.pack(side="left", padx=2)

# Дерево команд
commands_tree = ttk.Treeview(
    commands_tab,
    columns=("command_type", "command"),
    show="tree headings",
    selectmode="browse"
)

commands_tree.heading("#0", text="Наименование")
commands_tree.heading("command", text="Команда")

commands_tree.column("#0", width=220)
commands_tree.column("command", width=420)

commands_tree.pack(fill="both", expand=True)

status_name_var = tk.StringVar(value="")
status_connect_var = tk.StringVar(value="")
status_cmd_var = tk.StringVar(value="")

status_frame = ttk.Frame(frame_left)
status_frame.pack(fill="x", pady=(4, 0))

status_name_label = ttk.Label(
    status_frame,
    textvariable=status_name_var,
    anchor="w",
    font=("Segoe UI", 10, "bold")
)

status_name_label.pack(fill="x")

connect_frame = ttk.Frame(status_frame)
connect_frame.pack(fill="x")

status_connect_label = ttk.Label(
    connect_frame,
    textvariable=status_connect_var,
    anchor="w",
    foreground="#666666"
)

status_connect_label.pack(side="left", fill="x", expand=True)

status_cmd_label = ttk.Label(
    status_frame,
    textvariable=status_cmd_var,
    anchor="w",
    foreground="#888888"
)

status_cmd_label.pack(fill="x")

# считает базы в большом узле
def count_bases(nodes):
    total = 0

    for node in nodes:
        if node.get("type") == "base":
            if base_matches_filter(node):
                total += 1

        elif node.get("type") == "group":
            total += count_bases(node.get("children", []))

    return total


# Нормализация строки соединения (для копирования)
def normalize_connect_path(connect: str) -> str:
    connect = (connect or "").strip()

    lower = connect.lower()

    if lower.startswith("file="):
        path = connect[5:].strip()
        path = path.rstrip(";").strip()

        if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
            path = path[1:-1]

        return path

    if lower.startswith("srvr="):
        # Для серверной базы "путь" как файловый каталог не существует,
        # поэтому возвращаем строку соединения как есть.
        return connect.rstrip(";")

    if lower.startswith("ws="):
        return connect[3:].rstrip(";").strip()

    return connect.rstrip(";").strip()


def copy_to_clipboard(text):
    root.clipboard_clear()
    root.clipboard_append(text or "")
    root.update()


def get_selected_base():
    selected = tree.focus()
    if not selected:
        return None

    item = tree_nodes.get(selected)
    if not item or item.get("type") != "base":
        return None

    return item


def normalize_infobase_path(connect):
    connect = (connect or "").strip()
    lower = connect.lower()

    if lower.startswith("file="):
        path = connect[5:].strip().rstrip(";").strip()

        if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
            path = path[1:-1]

        return path

    if lower.startswith("ws="):
        return connect[3:].strip().rstrip(";").strip()

    return connect.rstrip(";").strip()


def copy_base_name():
    base = get_selected_base()
    if base:
        copy_to_clipboard(base.get("name", ""))


def copy_base_id():
    base = get_selected_base()
    if base:
        copy_to_clipboard(base.get("id", ""))


def copy_connection_string():
    base = get_selected_base()
    if base:
        copy_to_clipboard(base.get("connect", ""))


def copy_infobase_path():
    base = get_selected_base()
    if base:
        copy_to_clipboard(normalize_infobase_path(base.get("connect", "")))


btn_copy_connect = ttk.Menubutton(
    connect_frame,
    text="📋",
    width=3
)

copy_menu = tk.Menu(btn_copy_connect, tearoff=0)

copy_menu.add_command(
    label="Копировать наименование",
    command=copy_base_name
)

copy_menu.add_command(
    label="Копировать ID элемента",
    command=copy_base_id
)

copy_menu.add_separator()

copy_menu.add_command(
    label="Копировать строку соединения",
    command=copy_connection_string
)

copy_menu.add_command(
    label="Копировать путь к информационной базе",
    command=copy_infobase_path
)

btn_copy_connect["menu"] = copy_menu

btn_copy_connect.pack(side="right", padx=(4, 0))
ToolTip(btn_copy_connect, "Копировать строку подключения")

def copy_launch_command():
    cmd = status_cmd_var.get().strip()

    if not cmd:
        return

    pyperclip.copy(cmd)

copy_cmd_button = ttk.Button(
    status_frame,
    text="Копировать команду",
    command=copy_launch_command
)

copy_cmd_button.pack(anchor="e", pady=(2, 0))

# сохраняем ширину колонок списка
def save_column_widths():
    starter["column_widths"] = {
        "#0": tree.column("#0", "width"),
        "platform": tree.column("platform", "width"),
        "last_run": tree.column("last_run", "width"),
        "size": tree.column("size", "width")
    }

# функция загружает ширину колонок списка
def load_column_widths():
    widths = starter.get("column_widths", {})

    if "#0" in widths:
        tree.column("#0", width=widths["#0"])

    if "platform" in widths:
        tree.column("platform", width=widths["platform"])

    if "last_run" in widths:
        tree.column("last_run", width=widths["last_run"])

    if "size" in widths:
        tree.column("size", width=widths["size"])
        
def update_status():
    selected = tree.focus()

    if not selected or selected not in tree_nodes:
        status_name_var.set("")
        status_connect_var.set("")
        return

    base = tree_nodes[selected]

    status_name_var.set(base.get("name", ""))
    status_connect_var.set(base.get("connect", ""))
    status_cmd_var.set("")
    


# Поиск по Enter
def perform_search(event=None):
    global search_results, search_index

    query = search_var.get().strip().lower()
    if not query or query == SEARCH_PLACEHOLDER.lower():
        return "break"

    search_results = collect_search_results(query)
    search_index = -1
    find_next()

    return "break"

search_entry.bind("<Return>", perform_search)
search_results = []
search_index = -1


def collect_search_results(query):
    result = []

    def walk(parent=""):
        for iid in tree.get_children(parent):
            item = tree.item(iid)
            text = item["text"].lower()

            if query in text:
                result.append(iid)

            walk(iid)

    walk()
    return result


def find_next(event=None):
    global search_results, search_index

    query = search_var.get().strip().lower()
    if not query or query == SEARCH_PLACEHOLDER.lower():
        return "break"

    if not search_results:
        search_results = collect_search_results(query)
        search_index = -1

    if not search_results:
        return "break"

    search_index = (search_index + 1) % len(search_results)
    iid = search_results[search_index]

    tree.see(iid)
    tree.selection_set(iid)
    tree.focus(iid)

    return "break"


root.bind("<F3>", find_next)
search_entry.bind("<F3>", find_next)


# Ctrl+F → фокус в поиск
def focus_search(event=None):
    search_entry.focus()

    if search_var.get() == SEARCH_PLACEHOLDER:
        search_var.set("")

    search_entry.select_range(0, 'end')
    return "break"

root.bind("<Control-f>", focus_search)
root.bind("<Control-F>", focus_search)

# F5 → перезагрузка данных
def reload_data():
    global starter, favorites

    current_open_nodes = get_open_nodes()
    
    starter = load_json()
    starter["open_nodes"] = current_open_nodes
    favorites = starter.get("favorites", [])

    def refresh_sizes(nodes):
        for node in nodes:
            if node.get("type") == "group":
                refresh_sizes(node.get("children", []))

            elif node.get("type") == "base":
                connect = node.get("connect", "").strip()

                if connect.lower().startswith("file="):
                    path = connect[5:]
                    path = path.rstrip(";").strip()

                    if path.startswith('"') and path.endswith('"'):
                        path = path[1:-1]

                    today = datetime.date.today().isoformat()

                    if node.get("size_updated") == today:
                        continue
                        
                    db_file = os.path.join(path, "1Cv8.1CD")

                    if os.path.exists(db_file):
                        size_value = format_size(os.path.getsize(db_file))
                    else:
                        size_value = ""

                    node["size"] = size_value
                    node["size_updated"] = today

    refresh_sizes(starter.get("groups", []))
    refresh_sizes(starter.get("favorites", []))

    save_json(starter)
    populate_tree()

root.bind("<F5>", lambda e: reload_data())

def rename_selected_group():
    selected = tree.focus()

    if not selected or selected not in tree_nodes:
        return

    item = tree_nodes[selected]

    if item.get("type") != "group":
        return

    current_name = item.get("name", "")

    dialog = tk.Toplevel(root)
    dialog.title("Переименовать группу")
    dialog.transient(root)
    dialog.grab_set()

    center_window(root, dialog, 320, 120)

    ttk.Label(dialog, text="Новое имя группы:").pack(anchor="w", padx=10, pady=(10, 4))

    name_var = tk.StringVar(value=current_name)

    entry = ttk.Entry(dialog, textvariable=name_var)
    entry.pack(fill="x", padx=10, pady=4)
    entry.focus_set()

    def apply():
        new_name = name_var.get().strip()

        if not new_name:
            return

        item["name"] = new_name

        starter["open_nodes"] = get_open_nodes()
        save_json(starter)
        populate_tree()
        dialog.destroy()

    ttk.Button(dialog, text="Переименовать", command=apply).pack(pady=(6, 10))

# Home → вернуться в начало списка
def go_home(event=None):
    children = tree.get_children()

    if not children:
        return "break"

    first = children[0]

    tree.see(first)
    tree.selection_set(first)
    tree.focus(first)

    return "break"

root.bind("<Home>", go_home)

# определяем путь для стандартного Стартера
def resolve_1c_starter_path():
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES%\1cv8\common\1cestart.exe"),
        os.path.expandvars(r"%PROGRAMFILES(x86)%\1cv8\common\1cestart.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\1cv8\common\1cestart.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\1cv8_x86\common\1cestart.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\1cv8_x64\common\1cestart.exe"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def launch_1c_starter():
    starter_path = resolve_1c_starter_path()

    if not starter_path:
        messagebox.showerror(
            "Ошибка",
            "Не найден штатный стартер 1С.\n\n"
            "Проверьте каталог common в Program Files или LOCALAPPDATA."
        )
        return

    subprocess.Popen([starter_path])


def delete_selected_base():
    selected = tree.focus()
    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Удаление", "Выберите базу для удаления.")
        return

    base = tree_nodes[selected]
    name = base.get("name")
    connect = base.get("connect")

    if not messagebox.askyesno(
        "Подтверждение",
        f"Удалить базу «{name}» из списка?\n\nФайлы базы на диске удалены не будут."
    ):
        return

    # Удаляем из favorites
    global favorites
    favorites = [b for b in favorites if not (b.get("name") == name and b.get("connect") == connect)]
    starter["favorites"] = favorites

    # Удаляем из всех групп
    def remove_from_groups(groups):
        for group in groups:
            if group.get("type") == "group":
                group["children"] = [
                    b for b in group.get("children", [])
                    if not (b.get("type") == "base" and b.get("name") == name and b.get("connect") == connect)
                ]
                remove_from_groups(group["children"])

    remove_from_groups(starter.get("groups", []))
    save_json(starter)
    populate_tree()

# кнопка Удалить ИБ в меню
btn_delete = ttk.Button(
    toolbar,
    image=icon_delete,
    width=3,
    command=delete_selected_base
)
ToolTip(btn_delete, "Удалить базу из списка")

# Меню режимов запуска
menu_bar = ttk.Frame(frame_right)
menu_bar.pack(anchor="ne", pady=2, padx=2)

menu_bar.columnconfigure(0, minsize=110)
menu_bar.columnconfigure(1, minsize=24)

# Иконка для стартера
starter_icon = None

try:
    img_starter = Image.open(os.path.join(RESOURCE_DIR, "assets", "icons", "1c_starter.png"))
    img_starter = img_starter.resize((18, 18), Image.Resampling.LANCZOS)
    starter_icon = ImageTk.PhotoImage(img_starter)
except Exception as e:
    print(f"Иконка штатного стартера не загрузилась: {e}")


def create_launch_button(master, row, label, mode):
    def open_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    btn = ttk.Button(
        master,
        text=label,
        command=lambda: launch_selected_base(mode)
    )
    btn.grid(row=row, column=0, sticky="ew", pady=2)

    arrow = ttk.Button(
        master,
        text="▼",
        width=2
    )
    arrow.grid(row=row, column=1, sticky="ew", padx=(2, 0), pady=2)

    menu = tk.Menu(root, tearoff=0)

    menu.add_command(
        label="Запустить с выбором параметров",
        command=lambda: open_launch_params_dialog(mode)
    )

    menu.add_command(
        label="Запустить с аутентификацией",
        command=lambda: open_launch_params_dialog(mode, force_auth=True)
    )

    menu.add_command(
        label="Запустить от имени администратора",
        command=lambda: launch_selected_base(mode, run_as_admin=True)
    )

    arrow.bind("<Button-1>", open_menu)

    return btn, arrow


create_launch_button(menu_bar, 0, "1С:Предприятие", "enterprise")
create_launch_button(menu_bar, 1, "Конфигуратор", "configurator")

btn_starter = ttk.Button(
    menu_bar,
    text="1С:Стартер",
    image=starter_icon,
    compound="left",
    command=launch_1c_starter
)
btn_starter.image = starter_icon
btn_starter.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)

param_frame = ttk.LabelFrame(frame_right, text="Параметры запуска")
param_frame.pack(fill="x", pady=(10, 5))

ttklab = ttk.Label(param_frame, text="Интерфейс:")
ttklab.pack(anchor="w", pady=(10, 0))
interface = tk.StringVar(value="Auto")
ttk.Combobox(param_frame, values=["Auto", "Версия 8.5", "Такси", "Обычный"], textvariable=interface, state="readonly").pack(anchor="w")

starter = {}
favorites = []
tree_nodes = {}
commands_nodes = {}

def load_window_geometry():
    return starter.get("window_geometry", "900x600")

def save_window_geometry():
    starter["window_geometry"] = root.geometry()
    save_json(starter)

def get_open_nodes():
    open_ids = []

    def walk(parent=""):
        for iid in tree.get_children(parent):
            if tree.item(iid, "open"):
                if iid == "favorites":
                    open_ids.append("favorites")
                elif iid in tree_nodes:
                    item = tree_nodes[iid]
                    item_id = ensure_id(item)
                    open_ids.append(item_id)

            walk(iid)

    walk()
    return open_ids

def on_close():
    starter["window_geometry"] = root.geometry()
    starter["open_nodes"] = get_open_nodes()

    save_column_widths()

    save_json(starter)
    root.destroy()

def load_json():
    if not os.path.exists(STARTER_JSON):
        return {
            "favorites": [],
            "groups": [],
            "window_geometry": "900x600"
        }
    with open(STARTER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data):
    with open(STARTER_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Загрузка списка команд для вкладки "Команды"
def load_commands():
    if not os.path.exists(COMMANDS_JSON):
        return {"groups": []}

    with open(COMMANDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_commands(data):
    with open(COMMANDS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def format_size(size_bytes):
    for unit in ["Б", "КБ", "МБ", "ГБ", "ТБ"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"

        size_bytes /= 1024

    return f"{size_bytes:.1f} ПБ"


def calculate_folder_size(path):
    total = 0

    try:
        for root_dir, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root_dir, file)

                try:
                    total += os.path.getsize(file_path)
                except Exception:
                    pass

    except Exception:
        return ""

    return format_size(total)

def ensure_id(item):
    if not item.get("id"):
        item["id"] = str(uuid.uuid4())
    return item["id"]


def insert_item(parent, item):
    base_id = ensure_id(item)
    iid = base_id

    if parent == "favorites":
        iid = f"fav_{base_id}"

    values = (item.get("platform", ""), item.get("last_run", ""), item.get("size", ""))
    tree_nodes[iid] = item
    tree.insert(parent, "end", iid=iid, text=item["name"], values=values)

def base_matches_filter(item):
    selected_version = version_filter_var.get()

    if not selected_version:
        return True

    platform = item.get("platform", "")
    return platform.startswith(selected_version)


def group_has_visible_bases(children):
    for child in children:
        if child.get("type") == "base" and base_matches_filter(child):
            return True

        if child.get("type") == "group":
            if group_has_visible_bases(child.get("children", [])):
                return True

    return False

def insert_children(parent, children):
    sorted_children = sorted(
        children,
        key=lambda x: (
            x.get("type") != "group",
            not x.get("name", "").startswith("_"),
            x.get("name", "").lower()
        )
    )

    for child in sorted_children:
        if child.get("type") == "group":

            open_nodes = starter.get("open_nodes", [])
            group_id = ensure_id(child)
            gid = tree.insert(
                parent,
                "end",
                iid=group_id,
                text=child["name"],
                open=group_id in open_nodes
            )
            tree_nodes[gid] = child
            insert_children(gid, child.get("children", []))

        elif child.get("type") == "base":
            if base_matches_filter(child):
                insert_item(parent, child)

def open_launch_params_dialog(mode="enterprise", force_auth=False):
    selected = tree.focus()

    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Выбор", "Выберите базу")
        return

    base = tree_nodes[selected]

    if base.get("type") != "base":
        messagebox.showinfo("Выбор", "Выберите базу")
        return

    mode_title = "1С:Предприятие" if mode == "enterprise" else "Конфигуратор"

    dialog = tk.Toplevel(root)
    dialog.title(f"Параметры запуска {mode_title}")
    dialog.transient(root)
    dialog.grab_set()

    center_window(root, dialog, 620, 520)

    ttk.Label(
        dialog,
        text=base.get("name", ""),
        font=("Segoe UI", 10, "bold")
    ).pack(anchor="w", padx=10, pady=(10, 6))

    ttk.Separator(dialog).pack(fill="x", pady=(0, 8))

    ttk.Label(dialog, text="Строка параметров").pack(anchor="w", padx=10)

    params_var = tk.StringVar(value=base.get("parameters", ""))
    
    entry_params = ttk.Entry(dialog, textvariable=params_var)
    entry_params.pack(fill="x", padx=10, pady=(2, 8))
    
    if force_auth:
        dialog.after(100, entry_params.focus_set)
    
    entry_params.bind("<Control-v>", lambda e: entry_params.event_generate("<<Paste>>"))
    entry_params.bind("<Control-V>", lambda e: entry_params.event_generate("<<Paste>>"))

    entry_params.bind("<Control-c>", lambda e: entry_params.event_generate("<<Copy>>"))
    entry_params.bind("<Control-C>", lambda e: entry_params.event_generate("<<Copy>>"))

    entry_params.bind("<Control-x>", lambda e: entry_params.event_generate("<<Cut>>"))
    entry_params.bind("<Control-X>", lambda e: entry_params.event_generate("<<Cut>>"))

    table_frame = ttk.Frame(dialog)
    table_frame.pack(fill="both", expand=True, padx=10)

    columns = ("param", "mode", "description")

    params_tree = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings",
        height=10
    )

    params_tree.heading("param", text="Параметр")
    params_tree.heading("mode", text="Режим")
    params_tree.heading("description", text="Описание параметра")

    params_tree.column("param", width=150, stretch=False)
    params_tree.column("mode", width=110, stretch=False)
    params_tree.column("description", width=330, stretch=True)

    params_tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=params_tree.yview)
    params_tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    known_params = [
        ("UC", "Оба", "Обход блокировки сеанса"),
        ("ClearCache", "Оба", "Очистка кэша клиент-серверных вызовов"),
        ("DisableStartupMessages", "Оба", "Подавление стартовых сообщений"),
        ("AllowExecuteScheduledJobs -Off", "Предприятие", "Не запускать регламентные задания"),
        ("AllowExecuteScheduledJobs -On", "Предприятие", "Выполнять регламентные задания"),
        ("/Len", "Оба", "Использование английского интерфейса"),
        ("LogUI", "Оба", "Логирование действий пользователя"),
        ("UseHwLicenses+", "Оба", "Поиск локального ключа защиты выполняется"),
        ("UseHwLicenses-", "Оба", "Поиск локального ключа защиты не выполняется"),
        ("Out", "Оба", "Установка файла для вывода служебных сообщений"),
        ("DumpConfigToFiles", "Конфигуратор", "Выгрузка конфигурации в файлы"),
        ("LoadConfigFromFiles", "Конфигуратор", "Загрузка конфигурации из файлов"),
        ("UpdateDBCfg", "Конфигуратор", "Обновление конфигурации базы данных")
    ]

    allowed_mode = "Предприятие" if mode == "enterprise" else "Конфигуратор"

    for param, param_mode, desc in known_params:
        if param_mode in ("Оба", allowed_mode):
            params_tree.insert("", "end", values=(param, param_mode, desc))

    def add_selected_param():
        selected_param = params_tree.focus()
        if not selected_param:
            return

        values = params_tree.item(selected_param, "values")
        if not values:
            return

        param = values[0]
        current = params_var.get().strip()

        if param not in current:
            params_var.set((current + " " + param).strip())

    def edit_params():
        entry_params.focus_set()

    def clear_params():
        params_var.set("")

    params_tree.bind("<Double-1>", lambda e: add_selected_param())

    params_button_frame = ttk.Frame(dialog)
    params_button_frame.pack(fill="x", padx=10, pady=(6, 6))

    ttk.Button(params_button_frame, text="Добавить", command=add_selected_param).pack(side="left")
    ttk.Button(params_button_frame, text="Редактировать", command=edit_params).pack(side="left", padx=(6, 0))
    ttk.Button(params_button_frame, text="Очистить", command=clear_params).pack(side="left", padx=(6, 0))

    ttk.Separator(dialog).pack(fill="x", pady=(4, 8))

    run_as_admin_var = tk.BooleanVar(value=False)
    use_version_var = tk.BooleanVar(value=False)

    ttk.Checkbutton(
        dialog,
        text="Запустить от имени администратора",
        variable=run_as_admin_var
    ).pack(anchor="w", padx=10, pady=2)

    processing_frame = ttk.Frame(dialog)
    processing_frame.pack(fill="x", padx=10, pady=2)

    processing_var = tk.BooleanVar(value=False)

    ttk.Checkbutton(
        processing_frame,
        text="Запустить обработку:",
        variable=processing_var,
        state="disabled"
    ).pack(side="left")

    processing_entry = ttk.Entry(processing_frame, state="disabled")
    processing_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))

    version_frame = ttk.Frame(dialog)
    version_frame.pack(fill="x", padx=10, pady=(8, 4))

    ttk.Checkbutton(
        version_frame,
        text="Использовать версию:",
        variable=use_version_var
    ).pack(side="left")

    versions = get_installed_1c_versions()
    version_var = tk.StringVar(value=base.get("platform", ""))

    version_combo = ttk.Combobox(
        version_frame,
        textvariable=version_var,
        values=versions,
        state="readonly",
        width=18
    )
    version_combo.pack(side="left", padx=(6, 0))

    bottom = ttk.Frame(dialog)
    bottom.pack(fill="x", padx=10, pady=(8, 10))

    def continue_launch():
        forced_version = version_var.get().strip() if use_version_var.get() else ""

        launch_selected_base(
            mode=mode,
            extra_params=params_var.get().strip(),
            run_as_admin=run_as_admin_var.get(),
            forced_version=forced_version
        )

        dialog.after(100, dialog.destroy)

    ttk.Button(bottom, text="Отмена", command=dialog.destroy).pack(side="right")
    ttk.Button(bottom, text="Продолжить", command=continue_launch).pack(side="right", padx=(0, 8))

def populate_tree():
    tree_nodes.clear()
    tree.delete(*tree.get_children())

    open_nodes = starter.get("open_nodes", [])

    favorites_count = count_bases(favorites)
    favorites_title = f"★ Избранное ({favorites_count})"

    tree.insert(
        "",
        "end",
        iid="favorites",
        text=favorites_title,
        open=True
    )

    for fav in favorites:
        if base_matches_filter(fav):
            insert_item("favorites", fav)

    sorted_groups = sorted(
        starter.get("groups", []),
        key=lambda x: (
            not x.get("name", "").startswith("_"),
            x.get("name", "").lower()
        )
    )

    for group in sorted_groups:

        group_count = count_bases(group.get("children", []))
        group_title = f'{group["name"]} ({group_count})'

        group_id = ensure_id(group)
        gid = tree.insert(
            "",
            "end",
            iid=group_id,
            text=group_title,
            open=group_id in open_nodes
        )
        tree_nodes[gid] = group
        insert_children(gid, group.get("children", []))

# Генерация дерева команд
def populate_commands_tree():
    commands_nodes.clear()
    commands_tree.delete(*commands_tree.get_children())

    for group in commands_data.get("groups", []):
        group_name = group.get("name", "")
        group_id = ensure_id(group)

        gid = commands_tree.insert(
            "",
            "end",
            iid=group_id,
            text=group_name,
            open=True,
            values=("",)
        )

        commands_nodes[gid] = group

        for child in group.get("children", []):
            if child.get("type") != "command":
                continue

            command_id = ensure_id(child)

            commands_tree.insert(
                gid,
                "end",
                iid=command_id,
                text=child.get("name", ""),
                values=(
                    child.get("command", ""),
                )
            )

            commands_nodes[command_id] = child

#Открытие свойств выбранной команды
def open_selected_command_properties():
    selected = commands_tree.focus()

    if not selected or selected not in commands_nodes:
        messagebox.showinfo(
            "Свойства",
            "Выберите команду."
        )
        return

    item = commands_nodes[selected]

    if item.get("type") != "command":
        messagebox.showinfo(
            "Свойства",
            "Выберите команду."
        )
        return

    def on_save(updated):
        item.update(updated)

        save_commands(commands_data)
        populate_commands_tree()

    open_command_dialog(
        root,
        center_window,
        command_data=item,
        on_save=on_save
    )

# Добавление команды
def create_command():
    selected = commands_tree.focus()

    target_group = None

    if selected and selected in commands_nodes:
        item = commands_nodes[selected]

        if item.get("type") == "group":
            target_group = item
        elif item.get("type") == "command":
            parent_id = commands_tree.parent(selected)
            target_group = commands_nodes.get(parent_id)

    if target_group is None:
        groups = commands_data.get("groups", [])
        if groups:
            target_group = groups[0]
        else:
            target_group = {
                "type": "group",
                "name": "Программы",
                "children": []
            }
            commands_data["groups"] = [target_group]

    def on_save(new_command):
        ensure_id(new_command)
        target_group.setdefault("children", []).append(new_command)

        save_commands(commands_data)
        populate_commands_tree()

    open_command_dialog(
        root,
        center_window,
        command_data=None,
        on_save=on_save
    )

# Открытие формы отбора по версии платформы
def open_platform_filter_dialog():
    dialog = tk.Toplevel(root)
    dialog.title("Отбор по версии платформы")
    dialog.transient(root)
    dialog.grab_set()

    center_window(root, dialog, 260, 160)

    selected = tk.StringVar(value=version_filter_var.get() or "8.5")

    options = [
        ("1С:Предприятие 8.5", "8.5"),
        ("1С:Предприятие 8.3", "8.3"),
        ("1С:Предприятие 8.2", "8.2")
    ]

    for index, (text, value) in enumerate(options):
        ttk.Radiobutton(
            dialog,
            text=text,
            variable=selected,
            value=value
        ).pack(
            anchor="w",
            padx=14,
            pady=(10, 0) if index == 0 else (2, 0)
        )

    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=(12, 10))

    def apply_filter():
        value = selected.get()
        starter["open_nodes"] = get_open_nodes()
        version_filter_var.set(value)
        filter_button_text.set(value)
        populate_tree()
        dialog.destroy()

    def clear_filter():
        starter["open_nodes"] = get_open_nodes()
        version_filter_var.set("")
        filter_button_text.set("8.x")
        populate_tree()
        dialog.destroy()

    ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side="left")
    ttk.Button(button_frame, text="Без отбора", command=clear_filter).pack(side="right")
    ttk.Button(button_frame, text="Применить", command=apply_filter).pack(side="right", padx=(0, 5))

def on_register_save(result):
    base_entry = {
        "type": "base",
        "name": result.get("name", ""),
        "platform": result.get("platform", ""),
        "connect": result.get("connect", ""),
        "parameters": result.get("parameters", ""),
        "interface": result.get("interface", ""),
        "username": result.get("username", ""),
        "password": result.get("password", ""),
        "auth_enterprise": result.get("auth_enterprise", {
            "username": result.get("username", ""),
            "password": result.get("password", "")
        }),
        "last_run": "",
        "size": ""
    }

    selected = tree.focus()
    target_group = None

    if selected and selected in tree_nodes:
        selected_item = tree_nodes[selected]

        if selected_item.get("type") == "group":
            target_group = selected_item

        elif selected_item.get("type") == "base":
            parent_id = tree.parent(selected)

            if parent_id and parent_id in tree_nodes:
                parent_item = tree_nodes[parent_id]

                if parent_item.get("type") == "group":
                    target_group = parent_item

    if target_group is not None:
        target_group.setdefault("children", []).append(base_entry)

    elif starter.get("groups"):
        starter["groups"][0].setdefault("children", []).append(base_entry)

    else:
        starter["groups"] = [
            {
                "name": "Информационные базы",
                "type": "group",
                "children": [base_entry]
            }
        ]

    starter["open_nodes"] = get_open_nodes()

    save_json(starter)
    populate_tree()

def add_to_favorites():
    selected = tree.focus()

    if selected and selected in tree_nodes:
        item = tree_nodes[selected]

        if item.get("type") != "base":
            return

        if not any(
            f.get("name") == item.get("name")
            and f.get("connect") == item.get("connect")
            for f in favorites
        ):

            favorites.append(item.copy())
            starter["favorites"] = favorites
            starter["open_nodes"] = get_open_nodes()

            save_json(starter)
            populate_tree()

def update_base_everywhere(name, connect, updates):
    def walk(nodes):
        for node in nodes:
            if node.get("type") == "group":
                walk(node.get("children", []))
            elif node.get("type") == "base":
                if node.get("name") == name and node.get("connect") == connect:
                    node.update(updates)

    walk(starter.get("groups", []))

    for fav in starter.get("favorites", []):
        if fav.get("name") == name and fav.get("connect") == connect:
            fav.update(updates)

def open_properties(item_id):
    item = tree_nodes[item_id]

    def on_save(new_data):
        old_name = item.get("name")
        old_connect = item.get("connect")

        update_base_everywhere(old_name, old_connect, new_data)

        save_json(starter)
        populate_tree()

    open_properties_dialog(root, item.copy(), on_save)

def collect_group_paths():
    result = []

    def walk(groups, prefix=""):
        for group in groups:
            if group.get("type") != "group":
                continue

            name = group.get("name", "")
            path = f"{prefix}\\{name}" if prefix else name
            result.append(path)

            walk(group.get("children", []), path)

    walk(starter.get("groups", []))
    return result


def remove_base_from_groups(groups, name, connect):
    for group in groups:
        if group.get("type") != "group":
            continue

        children = group.get("children", [])

        for child in list(children):
            if (
                child.get("type") == "base"
                and child.get("name") == name
                and child.get("connect") == connect
            ):
                children.remove(child)
                return child

        found = remove_base_from_groups(children, name, connect)
        if found:
            return found

    return None


def add_base_to_group_path(groups, group_path, base):
    parts = group_path.split("\\")
    current = groups

    for part in parts:
        match = next(
            (
                g for g in current
                if g.get("type") == "group" and g.get("name") == part
            ),
            None
        )

        if not match:
            match = {
                "type": "group",
                "name": part,
                "children": []
            }
            current.append(match)

        current = match["children"]

    current.append(base)

def find_node_by_id(nodes, node_id):
    for node in nodes:
        if ensure_id(node) == node_id:
            return node

        if node.get("type") == "group":
            found = find_node_by_id(node.get("children", []), node_id)
            if found:
                return found

    return None


def remove_node_by_id(nodes, node_id):
    for node in list(nodes):
        if ensure_id(node) == node_id:
            nodes.remove(node)
            return node

        if node.get("type") == "group":
            found = remove_node_by_id(node.get("children", []), node_id)
            if found:
                return found

    return None


def is_descendant_group(parent_group, possible_child_id):
    for child in parent_group.get("children", []):
        if ensure_id(child) == possible_child_id:
            return True

        if child.get("type") == "group":
            if is_descendant_group(child, possible_child_id):
                return True

    return False

def move_selected_nodes():
    selected_ids = list(tree.selection())

    if not selected_ids:
        messagebox.showinfo("Перемещение", "Выберите базы или группы.")
        return

    movable = []

    for iid in selected_ids:
        item = tree_nodes.get(iid)

        if not item:
            continue

        if item.get("type") in ("base", "group"):
            movable.append(item)

    if not movable:
        messagebox.showinfo("Перемещение", "Нет выбранных элементов для перемещения.")
        return

    group_paths = collect_group_paths()

    if not group_paths:
        messagebox.showinfo("Перемещение", "Нет доступных групп.")
        return

    dialog = tk.Toplevel(root)
    dialog.title("Переместить в группу")
    dialog.transient(root)
    dialog.grab_set()

    center_window(root, dialog, 420, 150)

    ttk.Label(
        dialog,
        text=f"Выбрано элементов: {len(movable)}"
    ).pack(anchor="w", padx=10, pady=(10, 4))

    group_var = tk.StringVar(value=group_paths[0])

    combo = ttk.Combobox(
        dialog,
        textvariable=group_var,
        values=group_paths,
        state="readonly"
    )
    combo.pack(fill="x", padx=10, pady=4)

    def apply_move():
        target_path = group_var.get()
        target_group = find_group_by_path(starter.get("groups", []), target_path)

        if not target_group:
            messagebox.showerror("Перемещение", "Группа назначения не найдена.")
            return

        target_id = ensure_id(target_group)

        moved = []

        for item in movable:
            item_id = ensure_id(item)

            if item.get("type") == "group":
                if item_id == target_id or is_descendant_group(item, target_id):
                    continue

            removed = remove_node_by_id(starter.get("groups", []), item_id)

            if removed:
                moved.append(removed)

        target_group.setdefault("children", []).extend(moved)

        starter["open_nodes"] = get_open_nodes()
        starter["open_nodes"].append(target_id)

        save_json(starter)
        populate_tree()
        dialog.destroy()

    ttk.Button(dialog, text="Переместить", command=apply_move).pack(pady=(6, 10))

def find_group_by_path(groups, group_path):
    parts = group_path.split("\\")
    current = groups
    found = None

    for part in parts:
        found = next(
            (
                g for g in current
                if g.get("type") == "group" and g.get("name") == part
            ),
            None
        )

        if not found:
            return None

        current = found.get("children", [])

    return found


def show_context_menu(event):
    selected = tree.identify_row(event.y)
    if not selected:
        return

    current_selection = tree.selection()

    # Если правый клик был по уже выделенному элементу,
    # сохраняем множественное выделение.
    # Если по невыделенному — выбираем только его.
    if selected not in current_selection:
        tree.selection_set(selected)

    tree.focus(selected)

    item = tree_nodes.get(selected)
    if not item:
        return

    menu = tk.Menu(root, tearoff=0)

    current_selection = tree.selection()

    # Контекстное меню группы
    if item.get("type") == "group":
        if len(current_selection) == 1:
            menu.add_command(label="Переименовать группу...", command=rename_selected_group)
            menu.add_command(label="Удалить группу...", command=delete_selected_group)

        menu.add_command(label="Переместить в группу...", command=move_selected_nodes)
        menu.post(event.x_root, event.y_root)
        return

    # Контекстное меню базы
    if tree.parent(selected) == "favorites":
        def remove():
            favorites[:] = [
                f for f in favorites
                if not (
                    f.get("name") == item.get("name")
                    and f.get("connect") == item.get("connect")
                )
            ]
            starter["favorites"] = favorites
            save_json(starter)
            populate_tree()

        menu.add_command(label="Удалить из избранного", command=remove)
    else:
        menu.add_command(label="Добавить в избранное", command=add_to_favorites)

    menu.add_separator()
    menu.add_command(label="Переместить в группу...", command=move_selected_nodes)
    menu.add_command(label="Свойства", command=lambda: open_properties(selected))
    menu.add_command(label="Удалить из списка", command=delete_selected_base)
    menu.post(event.x_root, event.y_root)

# удалить группу
def delete_selected_group():
    selected = tree.focus()

    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Удаление группы", "Выберите группу.")
        return

    item = tree_nodes[selected]

    if item.get("type") != "group":
        messagebox.showinfo("Удаление группы", "Выберите группу.")
        return

    name = item.get("name", "")
    count = count_bases(item.get("children", []))

    if not messagebox.askyesno(
        "Подтверждение",
        f'Удалить группу "{name}"?\n\nБаз внутри: {count}\n\nСами базы 1С на диске удалены не будут.'
    ):
        return

    group_id = ensure_id(item)
    removed = remove_node_by_id(starter.get("groups", []), group_id)

    if not removed:
        messagebox.showerror("Удаление группы", "Не удалось найти группу в starter.json.")
        return

    starter["open_nodes"] = get_open_nodes()
    save_json(starter)
    populate_tree()

def get_installed_1c_versions():
    versions = []

    base_dirs = [
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "1cv8"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "1cv8")
    ]

    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue

        for name in os.listdir(base_dir):
            bin_dir = os.path.join(base_dir, name, "bin")
            exe_1cv8 = os.path.join(bin_dir, "1cv8.exe")
            exe_1cv8c = os.path.join(bin_dir, "1cv8c.exe")

            if os.path.exists(exe_1cv8) or os.path.exists(exe_1cv8c):
                versions.append(name)

    return sorted(set(versions), reverse=True)

def collect_bases_from_node(item_id):
    result = []

    item = tree_nodes.get(item_id)
    if item and item.get("type") == "base":
        result.append(item)
        return result

    for child_id in tree.get_children(item_id):
        result.extend(collect_bases_from_node(child_id))

    return result

def assign_platform_to_selected():
    selected = tree.focus()
    if not selected:
        messagebox.showinfo("Версия платформы", "Выберите группу или базу.")
        return

    bases = collect_bases_from_node(selected)
    if not bases:
        messagebox.showinfo("Версия платформы", "В выбранной группе нет баз.")
        return

    versions = get_installed_1c_versions()
    if not versions:
        messagebox.showerror("Версия платформы", "Установленные версии платформы не найдены.")
        return

    dialog = tk.Toplevel(root)
    dialog.title("Назначить версию платформы")
    dialog.transient(root)
    dialog.grab_set()
    dialog.lift()
    dialog.focus_force()

    center_window(root, dialog, 320, 140)

    ttk.Label(dialog, text=f"Баз будет обновлено: {len(bases)}").pack(anchor="w", padx=10, pady=(10, 4))

    platform_var = tk.StringVar(value=versions[0])
    combo = ttk.Combobox(dialog, textvariable=platform_var, values=versions, state="readonly", width=25)
    combo.pack(fill="x", padx=10, pady=4)
    combo.focus_set()

    def apply_version():
        selected_version = platform_var.get().strip()
        if not selected_version:
            return

        for base in bases:
            update_base_everywhere(
                base.get("name"),
                base.get("connect"),
                {"platform": selected_version}
            )

        save_json(starter)
        populate_tree()
        dialog.destroy()

    ttk.Button(dialog, text="Назначить", command=apply_version).pack(pady=(6, 10))

btn_platform = ttk.Button(
    toolbar,
    image=icon_version,
    width=3,
    command=assign_platform_to_selected
)
ToolTip(btn_platform, "Назначить версию платформы")
btn_platform.pack(side="left", padx=2) 

toolbar.icons = [
    icon_create,
    icon_copy,
    icon_group,
    icon_settings,
    icon_delete,
    icon_version
]

   
# Запуск выбранной информационной базы   
def launch_selected_base(mode="enterprise", extra_params="", run_as_admin=False, forced_version=""):
    print("launch mode:", mode)
    selected = tree.focus()
    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Выбор", "Выберите базу")
        return

    base = tree_nodes[selected]
    
    base_run_as_admin = base.get("run_as_admin", False)
    run_as_admin = run_as_admin or base_run_as_admin
    
    connect = base.get("connect", "")
    version = forced_version or base.get("platform", "")

    if not connect or not version:
        messagebox.showerror("Ошибка", "Отсутствует строка подключения или версия платформы.")
        return

    exe_path = resolve_1c_path(version, mode)
    if not exe_path:
        messagebox.showerror("Ошибка", f"Не найдена исполняемая программа для платформы {version}.")
        return

    connect_lower = connect.lower()

    # WS
    if "ws=" in connect_lower:
        ws_url = connect.split("=", 1)[1]
        ws_url = ws_url.rstrip(";").strip()

        if ws_url.startswith('"') and ws_url.endswith('"'):
            ws_url = ws_url[1:-1]

        arg = f'/WS"{ws_url}"'

    # Клиент-сервер
    elif "srvr=" in connect_lower:
        server_connect = connect.strip().replace('"', '')

        server = ""
        ref = ""

        for part in server_connect.split(";"):
            part = part.strip()

            if part.lower().startswith("srvr="):
                server = part.split("=", 1)[1].strip()

            elif part.lower().startswith("ref="):
                ref = part.split("=", 1)[1].strip()

        if not server or not ref:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось разобрать серверную строку:\n{connect}"
            )
            return

        arg = f'/S"{server}\\{ref}"'

    # Файловая
    else:
        path = connect.strip()

        if path.lower().startswith("file="):
            path = path[5:]

        path = path.rstrip(";").strip()

        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]

        arg = f'/F"{path}"'
  

    mode_flag = "ENTERPRISE"
    if mode == "configurator":
        mode_flag = "DESIGNER"

    cmd = f'"{exe_path}" {mode_flag} {arg}'

    username = (base.get("username") or "").strip()
    password = (base.get("password") or "").strip()

    auth_enterprise = base.get("auth_enterprise") or {}

    if not username:
        username = (auth_enterprise.get("username") or "").strip()

    if not password:
        password = (auth_enterprise.get("password") or "").strip()

    if username:
        cmd += f' /N"{username}"'

    if password:
        cmd += f' /P"{password}"'

    selected_interface = interface.get()

    if mode == "enterprise":
        if selected_interface == "Обычный":
            cmd += " /RunModeOrdinaryApplication"

        if selected_interface == "Такси":
            cmd += " /iTaxi"

        if selected_interface == "Версия 8.5":
            cmd += " /i85"
    
    if extra_params:
        cmd += f" {extra_params}"
    
    try:
        # status_var.set(cmd)
        status_cmd_var.set(cmd)
        if run_as_admin:
            args = cmd.replace(f'"{exe_path}" ', "", 1)

            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                exe_path,
                args,
                None,
                1
            )
        else:
            subprocess.Popen(cmd, shell=True)

        today = datetime.date.today().isoformat()

        update_base_everywhere(
            base.get("name"),
            base.get("connect"),
            {"last_run": today}
        )

        save_json(starter)
#        populate_tree()

    except Exception as e:
        messagebox.showerror("Ошибка запуска", str(e))

def launch_selected_command():
    selected = commands_tree.focus()

    if not selected or selected not in commands_nodes:
        return

    item = commands_nodes[selected]

    if item.get("type") != "command":
        return

    command = item.get("command", "").strip()
    parameters = item.get("parameters", "").strip()
    workdir = item.get("workdir", "").strip()

    if not command:
        messagebox.showerror(
            "Команда",
            "Не указана команда для запуска."
        )
        return

    cmd = f'"{command}"'

    if parameters:
        cmd += f" {parameters}"

    try:
        subprocess.Popen(
            cmd,
            cwd=workdir if workdir else None,
            shell=True
        )

    except Exception as e:
        messagebox.showerror(
            "Ошибка запуска",
            str(e)
        )

tree.bind("<<TreeviewSelect>>", lambda e: update_status())
tree.bind("<Button-3>", show_context_menu)
tree.bind("<Double-1>", lambda e: launch_selected_base())
commands_tree.bind(
    "<Double-1>",
    lambda e: launch_selected_command()
)



try:
    img = Image.open(os.path.join(RESOURCE_DIR, "assets", "sin_code.png"))
    img = img.resize((180, 180), Image.Resampling.LANCZOS)
    sin_photo = ImageTk.PhotoImage(img)
    label_sin = ttk.Label(frame_right, image=sin_photo, cursor="hand2")
    label_sin.image = sin_photo
    label_sin.pack(pady=10, anchor="se")
    label_sin.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/platform_morning"))
except Exception as e:
    print(f"Син не загрузился: {e}")



starter = load_json()
commands_data = load_commands()
root.geometry(load_window_geometry())
favorites = starter.get("favorites", [])
populate_tree()
populate_commands_tree()
load_column_widths()
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
