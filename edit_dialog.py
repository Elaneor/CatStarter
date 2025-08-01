import tkinter as tk
from tkinter import ttk
import os

def get_installed_1c_versions():
    versions = []
    base_dirs = [
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "1cv8"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "1cv8")
    ]
    for base_dir in base_dirs:
        if os.path.exists(base_dir):
            for name in os.listdir(base_dir):
                path = os.path.join(base_dir, name, "bin", "1cv8.exe")
                if os.path.exists(path):
                    versions.append(name)
    return sorted(set(versions))

def enable_ctrl_v(widget):
    def paste_event(event=None):
        try:
            widget.insert(tk.INSERT, widget.clipboard_get())
        except tk.TclError:
            pass
        return "break"
    widget.bind("<Control-v>", paste_event)
    widget.bind("<Control-V>", paste_event)

def create_connection_frame(master, base_type_var, entry_vars):
    frame = ttk.Frame(master)

    def update_fields():
        for widget in frame.winfo_children():
            widget.destroy()

        typ = base_type_var.get()

        if typ == "file":
            ttk.Label(frame, text="Каталог ИБ:").grid(row=0, column=0, sticky="w", pady=2)
            entry = ttk.Entry(frame)
            entry.grid(row=0, column=1, sticky="ew")
            enable_ctrl_v(entry)
            entry_vars["file"] = entry

        elif typ == "server":
            ttk.Label(frame, text="Сервер:").grid(row=0, column=0, sticky="w", pady=2)
            entry_s = ttk.Entry(frame)
            entry_s.grid(row=0, column=1, sticky="ew")
            enable_ctrl_v(entry_s)
            entry_vars["server"] = entry_s

            ttk.Label(frame, text="Имя базы:").grid(row=1, column=0, sticky="w", pady=2)
            entry_r = ttk.Entry(frame)
            entry_r.grid(row=1, column=1, sticky="ew")
            enable_ctrl_v(entry_r)
            entry_vars["ref"] = entry_r

        elif typ == "ws" or typ == "web":
            ttk.Label(frame, text="URL:").grid(row=0, column=0, sticky="w", pady=2)
            entry = ttk.Entry(frame)
            entry.grid(row=0, column=1, sticky="ew")
            enable_ctrl_v(entry)
            entry_vars["url"] = entry

        frame.columnconfigure(1, weight=1)

    base_type_var.trace_add("write", lambda *_: update_fields())
    update_fields()
    return frame

def open_properties_dialog(master, data, on_save):
    dialog = tk.Toplevel(master)
    dialog.title("Свойства базы")
    dialog.grab_set()

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Сведения
    frame_main = ttk.Frame(notebook)
    notebook.add(frame_main, text="1. Сведения")

    ttk.Label(frame_main, text="Наименование:").grid(row=0, column=0, sticky="w", pady=2)
    entry_name = ttk.Entry(frame_main)
    entry_name.insert(0, data.get("name", ""))
    entry_name.grid(row=0, column=1, sticky="ew")
    enable_ctrl_v(entry_name)

    ttk.Label(frame_main, text="Платформа:").grid(row=1, column=0, sticky="w", pady=2)
    versions = get_installed_1c_versions()
    entry_platform = ttk.Combobox(frame_main, values=versions, state="readonly")
    entry_platform.grid(row=1, column=1, sticky="ew")

    current_platform = data.get("platform", "")
    if current_platform in versions:
        entry_platform.set(current_platform)
    elif versions:
        entry_platform.set(versions[0])
    else:
        entry_platform.set(current_platform)

    ttk.Label(frame_main, text="Параметры запуска:").grid(row=2, column=0, sticky="w", pady=2)
    entry_params = ttk.Entry(frame_main)
    entry_params.grid(row=2, column=1, sticky="ew")
    entry_params.insert(0, data.get("parameters", ""))
    enable_ctrl_v(entry_params)

    ttk.Label(frame_main, text="Интерфейс:").grid(row=3, column=0, sticky="w", pady=2)
    combo_interface = ttk.Combobox(frame_main, values=["Auto", "Версия 8.5", "Такси", "Обычный"], state="readonly")
    combo_interface.grid(row=3, column=1, sticky="ew")
    combo_interface.set(data.get("interface", "Auto"))

    ttk.Label(frame_main, text="Дата последнего запуска:").grid(row=4, column=0, sticky="w", pady=2)
    entry_last_run = ttk.Entry(frame_main)
    entry_last_run.insert(0, data.get("last_run", ""))
    entry_last_run.grid(row=4, column=1, sticky="ew")
    enable_ctrl_v(entry_last_run)

    frame_main.columnconfigure(1, weight=1)

    # Подключение
    frame_conn = ttk.Frame(notebook)
    notebook.add(frame_conn, text="2. Подключение")

    connect = data.get("connect", "")
    base_type = tk.StringVar(value="file")
    if connect.startswith("Srvr="):
        base_type.set("server")
    elif connect.startswith("http") or connect.startswith("/WS"):
        base_type.set("ws")

    entry_vars = {}
    frame_connect = create_connection_frame(frame_conn, base_type, entry_vars)
    frame_connect.pack(fill="both", expand=True)

    if base_type.get() == "file":
        entry_vars["file"].insert(0, connect.replace("File=", "").strip(";"))
    elif base_type.get() == "server":
        parts = dict(part.split("=") for part in connect.strip(";").split(";") if "=" in part)
        entry_vars["server"].insert(0, parts.get("Srvr", ""))
        entry_vars["ref"].insert(0, parts.get("Ref", ""))
    elif base_type.get() == "ws":
        entry_vars["url"].insert(0, connect.strip())

    # Аутентификация
    frame_auth = ttk.Frame(notebook)
    notebook.add(frame_auth, text="3. Аутентификация")

    auth_mode = tk.StringVar(value=data.get("auth_mode", "auto"))
    auth_os = tk.BooleanVar(value=data.get("auth_os", False))

    ttk.Label(frame_auth, text="Аутентификация:").grid(row=0, column=0, sticky="w", pady=(5, 2))
    ttk.Radiobutton(frame_auth, text="Выбирать автоматически", variable=auth_mode, value="auto").grid(row=0, column=1, sticky="w")
    ttk.Radiobutton(frame_auth, text="Запрашивать имя и пароль", variable=auth_mode, value="manual").grid(row=1, column=1, sticky="w")

    row = 2
    ttk.Label(frame_auth, text="Пользователь:").grid(row=row, column=0, sticky="w")
    ent_user = ttk.Entry(frame_auth)
    ent_user.insert(0, data.get("auth_enterprise", {}).get("username", ""))
    ent_user.grid(row=row, column=1, sticky="ew")
    enable_ctrl_v(ent_user)

    row += 1
    ttk.Label(frame_auth, text="Пароль:").grid(row=row, column=0, sticky="w")
    ent_pass = ttk.Entry(frame_auth, show="*")
    ent_pass.insert(0, data.get("auth_enterprise", {}).get("password", ""))
    ent_pass.grid(row=row, column=1, sticky="ew")
    enable_ctrl_v(ent_pass)

    frame_auth.columnconfigure(1, weight=1)

    def save():
        if base_type.get() == "file":
            connect = f"File={entry_vars['file'].get().strip()};"
        elif base_type.get() == "server":
            s = entry_vars['server'].get().strip()
            r = entry_vars['ref'].get().strip()
            connect = f"Srvr={s};Ref={r};"
        elif base_type.get() == "ws":
            connect = entry_vars['url'].get().strip()
        else:
            connect = ""

        data["name"] = entry_name.get()
        data["platform"] = entry_platform.get()
        data["connect"] = connect
        data["parameters"] = entry_params.get()
        data["interface"] = combo_interface.get()
        data["last_run"] = entry_last_run.get()
        data["auth_mode"] = auth_mode.get()
        data["auth_os"] = auth_os.get()
        data["auth_enterprise"] = {
            "username": ent_user.get(),
            "password": ent_pass.get()
        }
        data["username"] = ent_user.get()
        data["password"] = ent_pass.get()

        on_save(data)
        dialog.destroy()

    ttk.Button(dialog, text="Сохранить", command=save).pack(pady=(0, 10))

def open_register_dialog(master, on_register):
    dialog = tk.Toplevel(master)
    dialog.title("Создание новой базы")
    dialog.grab_set()

    data = {
        "type": "file",
        "platform": "",
        "connect": "",
        "parameters": "",
        "interface": "Auto",
        "username": "",
        "password": "",
        "auth_mode": "auto",
        "auth_os": False,
        "auth_enterprise": {"username": "", "password": ""},
        "auth_designer": {"username": "", "password": ""},
        "last_run": ""
    }

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Вкладка 1: Тип базы
    frame_type = ttk.Frame(notebook)
    notebook.add(frame_type, text="1. Тип базы")

    base_type = tk.StringVar(value="file")
    ttk.Radiobutton(frame_type, text="Файловая", variable=base_type, value="file").pack(anchor="w", pady=2)
    ttk.Radiobutton(frame_type, text="Серверная", variable=base_type, value="server").pack(anchor="w", pady=2)
    ttk.Radiobutton(frame_type, text="WS-соединение", variable=base_type, value="ws").pack(anchor="w", pady=2)

    # Вкладка 2: Сведения
    frame_main = ttk.Frame(notebook)
    notebook.add(frame_main, text="2. Сведения")

    ttk.Label(frame_main, text="Наименование:").grid(row=0, column=0, sticky="w", pady=2)
    entry_name = ttk.Entry(frame_main)
    entry_name.grid(row=0, column=1, sticky="ew")
    enable_ctrl_v(entry_name)

    ttk.Label(frame_main, text="Платформа:").grid(row=1, column=0, sticky="w", pady=2)
    entry_platform = ttk.Combobox(frame_main, values=get_installed_1c_versions())
    entry_platform.grid(row=1, column=1, sticky="ew")
    enable_ctrl_v(entry_platform)

    entry_vars = {}
    frame_connect = create_connection_frame(frame_main, base_type, entry_vars)
    frame_connect.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=2)

    frame_main.columnconfigure(1, weight=1)

    # Вкладка 3: Дополнительно
    frame_extra = ttk.Frame(notebook)
    notebook.add(frame_extra, text="3. Дополнительно")

    ttk.Label(frame_extra, text="Параметры запуска:").grid(row=0, column=0, sticky="w", pady=2)
    entry_params = ttk.Entry(frame_extra)
    entry_params.grid(row=0, column=1, sticky="ew")
    enable_ctrl_v(entry_params)

    ttk.Label(frame_extra, text="Интерфейс:").grid(row=1, column=0, sticky="w", pady=2)
    combo_interface = ttk.Combobox(frame_extra, values=["Auto", "Версия 8.5", "Такси", "Обычный"], state="readonly")
    combo_interface.grid(row=1, column=1, sticky="ew")
    combo_interface.set("Auto")

    ttk.Label(frame_extra, text="Имя пользователя:").grid(row=2, column=0, sticky="w", pady=2)
    entry_username = ttk.Entry(frame_extra)
    entry_username.grid(row=2, column=1, sticky="ew")
    enable_ctrl_v(entry_username)

    ttk.Label(frame_extra, text="Пароль:").grid(row=3, column=0, sticky="w", pady=2)
    entry_password = ttk.Entry(frame_extra, show="*")
    entry_password.grid(row=3, column=1, sticky="ew")
    enable_ctrl_v(entry_password)

    auth_os_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame_extra, text="Аутентификация Windows (OS)", variable=auth_os_var).grid(row=4, column=1, sticky="w", pady=2)

    frame_extra.columnconfigure(1, weight=1)

    def save():
        if base_type.get() == "file":
            connect = f"File={entry_vars['file'].get().strip()};"
        elif base_type.get() == "server":
            s = entry_vars['server'].get().strip()
            r = entry_vars['ref'].get().strip()
            connect = f"Srvr={s};Ref={r};"
        elif base_type.get() == "ws":
            connect = entry_vars['url'].get().strip()
        else:
            connect = ""

        new_data = {
            "name": entry_name.get(),
            "platform": entry_platform.get(),
            "connect": connect,
            "parameters": entry_params.get(),
            "interface": combo_interface.get(),
            "username": entry_username.get(),
            "password": entry_password.get(),
            "auth_mode": "auto",
            "auth_enterprise": {
                "username": entry_username.get(),
                "password": entry_password.get()
            },
            "auth_designer": {
                "username": "",
                "password": ""
            },
            "auth_os": auth_os_var.get(),
            "last_run": ""
        }
        on_register(new_data)
        dialog.destroy()

    ttk.Button(dialog, text="Создать", command=save).pack(pady=(0, 10))