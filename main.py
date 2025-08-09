# canvas smoke test
import json
import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import shlex
import webbrowser
from PIL import Image, ImageTk
from edit_dialog import open_register_dialog, open_properties_dialog
from settings_dialog import open_settings_dialog, load_settings, parse_v8i_file

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STARTER_JSON = os.path.join(APP_DIR, "starter.json")

def load_json():
    if not os.path.exists(STARTER_JSON):
        return {"favorites": [], "groups": []}
    with open(STARTER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data):
    with open(STARTER_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

starter = load_json()
favorites = starter.get("favorites", [])

settings = load_settings()
v8i_paths = settings.get("v8i_paths", [])

root = tk.Tk()
root.iconbitmap(os.path.join(APP_DIR, "assets", "cat.ico"))
root.title("Cat Starter")
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


def insert_item(parent, item):
    iid = f"{parent}_{item['name']}"
    values = (item.get("platform", ""), item.get("last_run", ""), item.get("size", ""))
    tree_nodes[iid] = item
    tree.insert(parent, "end", iid=iid, text=item["name"], values=values)

def insert_children(parent, children):
    for child in children:
        if child.get("type") == "group":
            name = child["name"]
            if "platform" in child:
                name += f" ({child['platform']})"
            gid = tree.insert(parent, "end", text=name, open=True)
            insert_children(gid, child.get("children", []))
        elif child.get("type") == "base":
            insert_item(parent, child)

def populate_tree():
    tree.delete(*tree.get_children())
    tree.insert("", "end", iid="favorites", text="★ Избранное", open=True)
    for fav in favorites:
        insert_item("favorites", fav)
    for group in starter.get("groups", []):
        gid = tree.insert("", "end", text=group["name"], open=True)
        insert_children(gid, group.get("children", []))

# Дерево баз
columns = ("platform", "last_run", "size")
tree = ttk.Treeview(frame_left, columns=columns, show="tree headings")
tree.heading("#0", text="Наименование")
tree.heading("platform", text="Платформа")
tree.heading("last_run", text="Дата")
tree.heading("size", text="Размер")
tree.pack(fill="both", expand=True)

tree_nodes = {}



existing_connects = set()

def collect_connects(groups):
    for g in groups:
        if g.get("type") == "base":
            existing_connects.add(g.get("connect"))
        elif g.get("type") == "group":
            collect_connects(g.get("children", []))

collect_connects(starter.get("groups", []))

for v8i_path in v8i_paths:
    if not os.path.exists(v8i_path):
        continue
    try:
        imported = parse_v8i_file(v8i_path)
        for b in imported:
            if b["connect"] in existing_connects:
                continue
            base_entry = {
                "type": "base",
                "name": b["name"],
                "platform": b.get("platform", ""),
                "connect": b["connect"],
                "last_run": "",
                "size": "",
                "parameters": b.get("parameters", ""),
                "interface": b.get("interface", "Auto"),
                "auth_mode": b.get("auth_mode", "auto"),
                "auth_os": b.get("auth_os", False),
                "username": b.get("username", ""),
                "password": b.get("password", ""),
                "auth_enterprise": b.get("auth_enterprise", {"username": "", "password": ""}),
                "auth_designer": b.get("auth_designer", {"username": "", "password": ""})
            }

            folder = b.get("folder", "").strip()
            v8i_root = next((g for g in starter["groups"] if g.get("name") == "🗂 Импорт из .v8i"), None)
            if not v8i_root:
                v8i_root = {"type": "group", "name": "🗂 Импорт из .v8i", "children": []}
                starter["groups"].append(v8i_root)
            current = v8i_root["children"]

            if folder and folder not in ["/", "\\"]:
                parts = folder.split("\\") if "\\" in folder else folder.split("/")
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    match = next((g for g in current if g.get("type") == "group" and g.get("name") == part), None)
                    if not match:
                        match = {"type": "group", "name": part, "children": []}
                        current.append(match)
                    current = match["children"]

            current.append(base_entry)
            existing_connects.add(b["connect"])
    except Exception as e:
        print(f"[!] Ошибка при импорте {v8i_path}: {e}")

save_json(starter)


populate_tree()

# Поиск по Enter
def perform_search(event=None):
    query = search_var.get().strip().lower()
    if not query:
        return
    for iid in tree.get_children("favorites"):
        item = tree.item(iid)
        if query in item["text"].lower():
            tree.see(iid)
            tree.selection_set(iid)
            tree.focus(iid)
            return
    for top_id in tree.get_children():
        for iid in tree.get_children(top_id):
            item = tree.item(iid)
            if query in item["text"].lower():
                tree.see(iid)
                tree.selection_set(iid)
                tree.focus(iid)
                return



# Ctrl+F → фокус в поиск
def focus_search(event=None):
    search_entry.focus()
    search_entry.select_range(0, 'end')
    return "break"

root.bind("<Control-f>", focus_search)

# F5 → перезагрузка данных
def reload_data():
    global starter, favorites
    starter = load_json()
    favorites = starter.get("favorites", [])
    populate_tree()

root.bind("<F5>", lambda e: reload_data())

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



# кнопки панели
search_var = tk.StringVar()
search_entry = ttk.Entry(toolbar, textvariable=search_var)
search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
search_entry.insert(0, "\U0001F50D Поиск...")

search_entry.bind("<Return>", perform_search)

btn_create = ttk.Button(toolbar, text="Создать ИБ", command=lambda: open_register_dialog(root, on_register_save))
btn_duplicate = ttk.Button(toolbar, text="Дублировать ИБ")
btn_group = ttk.Button(toolbar, text="Создать группу")
btn_delete = ttk.Button(toolbar, text="Удалить ИБ", command=delete_selected_base)
btn_settings = ttk.Button(toolbar, text="⚙️ Настройки", command=lambda: open_settings_dialog(root))

btn_create.pack(side="left", padx=2)
btn_duplicate.pack(side="left", padx=2)
btn_group.pack(side="left", padx=2)
btn_delete.pack(side="left", padx=2)
btn_settings.pack(side="left", padx=2)


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
for text, val in [("Предприятие", "enterprise"), ("Конфигуратор", "configurator"), ("Тест", "test")]:
    ttk.Radiobutton(param_frame, text=text, variable=launch_mode, value=val).pack(anchor="w")

ttklab = ttk.Label(param_frame, text="Интерфейс:")
ttklab.pack(anchor="w", pady=(10, 0))
interface = tk.StringVar(value="Auto")
ttk.Combobox(param_frame, values=["Auto", "Версия 8.5", "Такси", "Обычный"], textvariable=interface, state="readonly").pack(anchor="w")

session_var = tk.BooleanVar(value=True)
ttk.Checkbutton(param_frame, text="Текущая сессия", variable=session_var).pack(anchor="w")




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
        "auth_mode": result.get("auth_mode", "auto"),
        "auth_os": result.get("auth_os", False),
        "auth_enterprise": result.get("auth_enterprise", {
            "username": result.get("username", ""),
            "password": result.get("password", "")
        }),
        "auth_designer": result.get("auth_designer", {
            "username": "",
            "password": ""
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
        if not any(f.get("name") == item.get("name") and f.get("connect") == item.get("connect") for f in favorites):
            favorites.append(item.copy())
            starter["favorites"] = favorites
            save_json(starter)
            populate_tree()

def open_properties(item_id):
    def on_save(new_data):
        # Обновляем ссылку на саму базу
        tree_nodes[item_id].update(new_data)

        # Обновляем имя в дереве
        tree.item(item_id, text=new_data["name"])

        # Сохраняем файл
        save_json(starter)

    open_properties_dialog(root, tree_nodes[item_id].copy(), on_save)

def show_context_menu(event):
    selected = tree.identify_row(event.y)
    if not selected:
        return
    tree.selection_set(selected)
    item = tree_nodes.get(selected)
    if not item:
        return
    menu = tk.Menu(root, tearoff=0)
    if selected.startswith("favorites_"):
        def remove():
            if item in favorites:
                favorites.remove(item)
                starter["favorites"] = favorites
                save_json(starter)
                populate_tree()
        menu.add_command(label="Удалить из избранного", command=remove)
    else:
        menu.add_command(label="Добавить в избранное", command=add_to_favorites)
    menu.add_separator()
		
		
    menu.add_command(label="Свойства", command=lambda: open_properties(selected))
    menu.add_command(label="Удалить ИБ", command=delete_selected_base)
    menu.post(event.x_root, event.y_root)

def resolve_1c_path(version):
    base_dirs = [
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "1cv8", version, "bin"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "1cv8", version, "bin")
    ]
    for base_dir in base_dirs:
        if os.path.exists(os.path.join(base_dir, "1cv8c.exe")):
            return os.path.join(base_dir, "1cv8c.exe")
        elif os.path.exists(os.path.join(base_dir, "1cv8.exe")):
            return os.path.join(base_dir, "1cv8.exe")
    return None

def get_inherited_platform(item_id):
    item = tree_nodes.get(item_id)
    if item.get("platform"):
        return item["platform"]

    parent = tree.parent(item_id)
    while parent:
        parent_item = tree.item(parent)
        parent_data = tree_nodes.get(parent)
        if parent_data and parent_data.get("platform"):
            return parent_data["platform"]
        parent = tree.parent(parent)
    return ""



def launch_selected_base():
    selected = tree.focus()
    if not selected or selected not in tree_nodes:
        messagebox.showinfo("Выбор", "Выберите базу")
        return

    base = tree_nodes[selected]
    connect = base.get("connect", "")
    version = get_inherited_platform(selected)
    if not connect or not version:
        messagebox.showerror("Ошибка", "Отсутствует строка подключения или версия платформы.")
        return

    exe_path = resolve_1c_path(version)
    if not exe_path:
        messagebox.showerror("Ошибка", f"Не найдена исполняемая программа для платформы {version}.")
        return

    mode = launch_mode.get()

    # Аргумент строки подключения
    connect_lower = connect.lower()
    if "ws=" in connect_lower:
        ws_url = connect.split("ws=", 1)[-1].split(";", 1)[0]
        arg = f'/WS"{ws_url}"'
    elif "srvr=" in connect_lower:
        arg = f"/S{connect.replace(';','')}"
    else:
        path = connect.replace("File=", "").replace(";", "")
        arg = f'/F"{path}"'

    # Режим запуска
    mode_flag = "ENTERPRISE"
    if mode == "configurator":
        mode_flag = "DESIGNER"
    elif mode == "test":
        mode_flag = "ENTERPRISE /C"

    cmd = [exe_path] + mode_flag.split() + shlex.split(arg)

    # Аутентификация
    username = ""
    password = ""

    auth_mode = base.get("auth_mode", "auto")
    auth_os = base.get("auth_os", False)

    if not auth_os:
        if mode == "enterprise":
            auth_data = base.get("auth_enterprise", {})
        elif mode == "configurator":
            auth_data = base.get("auth_designer", {})
        else:
            auth_data = {}
        username = auth_data.get("username", "")
        password = auth_data.get("password", "")

    if username:
        cmd.append(f"/N{username}")
    if password:
        cmd.append(f"/P{password}")

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        messagebox.showerror("Ошибка запуска", str(e))

tree.bind("<Button-3>", show_context_menu)
tree.bind("<Double-1>", lambda e: launch_selected_base())
ttk.Button(frame_right, text="Запустить", command=launch_selected_base).pack(pady=10, anchor="se")

try:
    img = Image.open(os.path.join(APP_DIR, "assets", "sin_code.png"))
    img = img.resize((180, 180), Image.Resampling.LANCZOS)
    sin_photo = ImageTk.PhotoImage(img)
    label_sin = ttk.Label(frame_right, image=sin_photo, cursor="hand2")
    label_sin.image = sin_photo
    label_sin.pack(pady=10, anchor="se")
    label_sin.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/platform_morning"))
except Exception as e:
    print(f"Син не загрузился: {e}")


root.mainloop()