import ctypes
import datetime
import json
import tkinter as tk
from tkinter import ttk, messagebox
import os
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
search_entry = ttk.Entry(toolbar, textvariable=search_var)
search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
SEARCH_PLACEHOLDER = "\U0001F50D Поиск..."
search_var.set(SEARCH_PLACEHOLDER)

def clear_search_placeholder(event=None):
    if search_var.get() == SEARCH_PLACEHOLDER:
        search_var.set("")

search_entry.bind("<FocusIn>", clear_search_placeholder)

btn_create = ttk.Button(
    toolbar,
    image=icon_create,
    text="Создать",
    compound="left",
    command=lambda: open_register_dialog(root, on_register_save)
)

btn_duplicate = ttk.Button(
    toolbar,
    image=icon_copy,
    text="Копия",
    compound="left"
)

btn_group = ttk.Button(
    toolbar,
    image=icon_group,
    text="Группа",
    compound="left"
)

btn_create.pack(side="left", padx=2)
btn_duplicate.pack(side="left", padx=2)
btn_group.pack(side="left", padx=2)

btn_settings = ttk.Button(
    toolbar,
    image=icon_settings,
    text="Настройки",
    compound="left",
    command=lambda: open_settings_dialog(root, reload_data)
)
btn_settings.pack(side="left", padx=2)

# Дерево баз
columns = ("platform", "last_run", "size")
tree = ttk.Treeview(frame_left, columns=columns, show="tree headings")
tree.heading("#0", text="Наименование")
tree.heading("platform", text="Платформа")
tree.heading("last_run", text="Дата")
tree.heading("size", text="Размер")
tree.pack(fill="both", expand=True)

status_var = tk.StringVar(value="")

status_label = ttk.Label(
    frame_left,
    textvariable=status_var,
    anchor="w"
)

status_label.pack(fill="x", pady=(4, 0))

def update_status():
    selected = tree.focus()

    if not selected or selected not in tree_nodes:
        status_var.set("")
        return

    base = tree_nodes[selected]

    text = (
        f'{base.get("name", "")} | '
        f'{base.get("platform", "")} | '
        f'{base.get("connect", "")}'
    )

    status_var.set(text)

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
    search_entry.select_range(0, 'end')
    return "break"

root.bind("<Control-f>", focus_search)
root.bind("<Control-F>", focus_search)

# F5 → перезагрузка данных
def reload_data():
    global starter, favorites
    starter = load_json()
    favorites = starter.get("favorites", [])
    populate_tree()

root.bind("<F5>", lambda e: reload_data())

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


def delete_selected_base():
    selected = tree.focus()
    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Удаление", "Выберите базу для удаления.")
        return

    base = tree_nodes[selected]
    name = base.get("name")
    connect = base.get("connect")

    if not messagebox.askyesno("Подтверждение", f"Удалить базу «{name}»?"):
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
    text="Удалить",
    compound="left",
    command=delete_selected_base
)
btn_delete.pack(side="left", padx=2)

# Меню режимов запуска
menu_bar = ttk.Frame(frame_right)
menu_bar.pack(anchor="ne", pady=2, padx=2)

def create_menu_button(master, label, options):
    btn = ttk.Menubutton(master, text=label, direction="below")
    menu = tk.Menu(btn, tearoff=0)
    for name in options:
        menu.add_command(label=name)
    btn["menu"] = menu
    btn.pack(anchor="ne", pady=2, padx=2)
    return btn

create_menu_button(menu_bar, "1С:Предприятие", ["Авто", "Обычный", "Толстый", "Тонкий"])
create_menu_button(menu_bar, "Конфигуратор", ["Стандартный", "С параметрами..."])

param_frame = ttk.LabelFrame(frame_right, text="Параметры запуска")
param_frame.pack(fill="x", pady=(10, 5))

launch_mode = tk.StringVar(value="enterprise")
for text, val in [("Предприятие", "enterprise"), ("Конфигуратор", "configurator")]:
    ttk.Radiobutton(param_frame, text=text, variable=launch_mode, value=val).pack(anchor="w")

ttklab = ttk.Label(param_frame, text="Интерфейс:")
ttklab.pack(anchor="w", pady=(10, 0))
interface = tk.StringVar(value="Auto")
ttk.Combobox(param_frame, values=["Auto", "Версия 8.5", "Такси", "Обычный"], textvariable=interface, state="readonly").pack(anchor="w")

starter = {}
favorites = []
tree_nodes = {}

def load_window_geometry():
    return starter.get("window_geometry", "900x600")

def save_window_geometry():
    starter["window_geometry"] = root.geometry()
    save_json(starter)

def on_close():
    save_window_geometry()
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

def insert_children(parent, children):
    for child in children:
        if child.get("type") == "group":
            gid = tree.insert(parent, "end", text=child["name"], open=True)
            insert_children(gid, child.get("children", []))
        elif child.get("type") == "base":
            insert_item(parent, child)

def populate_tree():
    tree_nodes.clear()
    tree.delete(*tree.get_children())

    tree.insert("", "end", iid="favorites", text="★ Избранное", open=True)

    for fav in favorites:
        insert_item("favorites", fav)

    for group in starter.get("groups", []):
        gid = tree.insert("", "end", text=group["name"], open=True)
        insert_children(gid, group.get("children", []))

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
    if starter.get("groups"):
        starter["groups"][0]["children"].append(base_entry)
    else:
        starter["groups"] = [{"name": "Информационные базы", "type": "group", "children": [base_entry]}]
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


def move_selected_base():
    selected = tree.focus()

    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Перемещение", "Выберите базу.")
        return

    item = tree_nodes[selected]

    if item.get("type") != "base":
        messagebox.showinfo("Перемещение", "Выберите базу, а не группу.")
        return

    group_paths = collect_group_paths()

    if not group_paths:
        messagebox.showinfo("Перемещение", "Нет доступных групп.")
        return

    dialog = tk.Toplevel(root)
    dialog.title("Переместить в группу")
    dialog.transient(root)
    dialog.grab_set()

    center_window(root, dialog, 420, 140)

    ttk.Label(dialog, text=f'База: {item.get("name", "")}').pack(anchor="w", padx=10, pady=(10, 4))

    group_var = tk.StringVar(value=group_paths[0])

    combo = ttk.Combobox(
        dialog,
        textvariable=group_var,
        values=group_paths,
        state="readonly"
    )
    combo.pack(fill="x", padx=10, pady=4)

    def apply_move():
        name = item.get("name")
        connect = item.get("connect")

        moved_base = remove_base_from_groups(starter.get("groups", []), name, connect)

        if not moved_base:
            moved_base = item.copy()

        add_base_to_group_path(starter.get("groups", []), group_var.get(), moved_base)

        save_json(starter)
        populate_tree()
        dialog.destroy()

    ttk.Button(dialog, text="Переместить", command=apply_move).pack(pady=(6, 10))

def show_context_menu(event):
    selected = tree.identify_row(event.y)
    if not selected:
        return

    tree.selection_set(selected)
    tree.focus(selected)

    item = tree_nodes.get(selected)
    if not item:
        return

    menu = tk.Menu(root, tearoff=0)

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
    menu.add_command(label="Переместить в группу...", command=move_selected_base)
    menu.add_command(label="Свойства", command=lambda: open_properties(selected))
    menu.add_command(label="Удалить ИБ", command=delete_selected_base)
    menu.post(event.x_root, event.y_root)

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
    text="Версия",
    compound="left",
    command=assign_platform_to_selected
)
btn_platform.pack(side="left", padx=2) 

toolbar.icons = [
    icon_create,
    icon_copy,
    icon_group,
    icon_settings,
    icon_delete,
    icon_version
]

def resolve_1c_path(version):
    def find_exe(ver):
        base_dirs = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "1cv8", ver, "bin"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "1cv8", ver, "bin")
        ]

        for base_dir in base_dirs:
            exe_1cv8c = os.path.join(base_dir, "1cv8c.exe")
            exe_1cv8 = os.path.join(base_dir, "1cv8.exe")

            selected_interface = interface.get()

            if selected_interface == "Обычный":
                if os.path.exists(exe_1cv8):
                    return exe_1cv8
                if os.path.exists(exe_1cv8c):
                    return exe_1cv8c
            else:
                if os.path.exists(exe_1cv8c):
                    return exe_1cv8c
                if os.path.exists(exe_1cv8):
                    return exe_1cv8

        return None

    # 1. Сначала ищем точную версию
    exact = find_exe(version)
    if exact:
        return exact

    # 2. Если точной нет, ищем ближайшую установленную того же семейства
    # Например, для 8.5.1.536 подойдет 8.5.4.1253
    parts = version.split(".")
    if len(parts) >= 2:
        family = ".".join(parts[:2])
        installed_versions = get_installed_1c_versions()

        family_versions = [
            v for v in installed_versions
            if v.startswith(family + ".")
        ]

        if family_versions:
            fallback = family_versions[0]
            return find_exe(fallback)

    return None
            
def launch_selected_base():
    selected = tree.focus()
    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Выбор", "Выберите базу")
        return

    base = tree_nodes[selected]
    connect = base.get("connect", "")
    version = base.get("platform", "")

    if not connect or not version:
        messagebox.showerror("Ошибка", "Отсутствует строка подключения или версия платформы.")
        return

    exe_path = resolve_1c_path(version)
    if not exe_path:
        messagebox.showerror("Ошибка", f"Не найдена исполняемая программа для платформы {version}.")
        return

    mode = launch_mode.get()
    connect_lower = connect.lower()

    # WS
    if "ws=" in connect_lower:
        ws_url = connect.split("ws=", 1)[-1].split(";", 1)[0]
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

    if not username and not password:
        auth_enterprise = base.get("auth_enterprise") or {}
        username = (auth_enterprise.get("username") or "").strip()
        password = (auth_enterprise.get("password") or "").strip()

    if username:
        cmd += f' /N"{username}"'

    if password:
        cmd += f' /P"{password}"'

    selected_interface = interface.get()
    
    if selected_interface == "Обычный":
        cmd += " /RunModeOrdinaryApplication"
    
    if selected_interface == "Такси":
        cmd += " /iTaxi"
        
    if selected_interface == "Версия 8.5":
        cmd += " /i85"
    
    
    try:
        status_var.set(cmd)
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

tree.bind("<<TreeviewSelect>>", lambda e: update_status())
tree.bind("<Button-3>", show_context_menu)
tree.bind("<Double-1>", lambda e: launch_selected_base())
ttk.Button(frame_right, text="Запустить", command=launch_selected_base).pack(pady=10, anchor="se")

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
root.geometry(load_window_geometry())
favorites = starter.get("favorites", [])
populate_tree()
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
