import os
import tkinter as tk
from tkinter import ttk
import datetime

def enable_ctrl_v(widget):
    widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
    widget.bind("<Control-V>", lambda e: widget.event_generate("<<Paste>>"))

def center_window(parent, window, width=500, height=400):
    parent.update_idletasks()

    x = parent.winfo_x()
    y = parent.winfo_y()
    w = parent.winfo_width()
    h = parent.winfo_height()

    pos_x = x + (w // 2) - (width // 2)
    pos_y = y + (h // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

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

def open_properties_dialog(master, data, on_save):
    dialog = tk.Toplevel(master)
    dialog.title("Свойства базы")
    dialog.transient(master)
    dialog.grab_set()
    dialog.lift()
    dialog.focus_force()

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    frame_general = ttk.Frame(notebook)
    notebook.add(frame_general, text="1. Сведения")
    frame_general.columnconfigure(1, weight=1)

    frame_connection = ttk.Frame(notebook)
    notebook.add(frame_connection, text="2. Подключение")
    frame_connection.columnconfigure(1, weight=1)

    frame_auth = ttk.Frame(notebook)
    notebook.add(frame_auth, text="3. Аутентификация")
    frame_auth.columnconfigure(1, weight=1)

    frame_launch = ttk.Frame(notebook)
    notebook.add(frame_launch, text="4. Параметры запуска")
    frame_launch.columnconfigure(1, weight=1)

    ttk.Label(frame_general, text="Наименование:").grid(row=0, column=0, sticky="w", pady=2)
    entry_name = ttk.Entry(frame_general)
    entry_name.grid(row=0, column=1, pady=2, sticky="ew")
    entry_name.insert(0, data.get("name", ""))
    enable_ctrl_v(entry_name)

    ttk.Label(frame_general, text="Платформа:").grid(row=1, column=0, sticky="w", pady=2)
    versions = get_installed_1c_versions()

    entry_platform = ttk.Combobox(frame_general, values=versions)
    entry_platform.grid(row=1, column=1, pady=2, sticky="ew")
    entry_platform.set(data.get("platform", ""))

    enable_ctrl_v(entry_platform)

    ttk.Label(frame_connection, text="Подключение:").grid(row=0, column=0, sticky="w", pady=2)
    entry_connect = ttk.Entry(frame_connection)
    entry_connect.grid(row=0, column=1, pady=2, sticky="ew")
    entry_connect.insert(0, data.get("connect", ""))
    enable_ctrl_v(entry_connect)

    ttk.Label(frame_general, text="Интерфейс:").grid(row=2, column=0, sticky="w", pady=2)
    combo_interface = ttk.Combobox(frame_general, values=["Auto", "Версия 8.5", "Такси", "Обычный"], state="readonly")
    combo_interface.grid(row=2, column=1, pady=2, sticky="ew")
    combo_interface.set(data.get("interface", "Auto"))

    ttk.Label(frame_general, text="Дата последнего запуска:").grid(row=3, column=0, sticky="w", pady=2)
    entry_last_run = ttk.Entry(frame_general)
    entry_last_run.grid(row=3, column=1, pady=2, sticky="ew")
    entry_last_run.insert(0, data.get("last_run", ""))
    enable_ctrl_v(entry_last_run)

    ttk.Label(frame_auth, text="Имя пользователя:").grid(row=0, column=0, sticky="w", pady=2)
    entry_username = ttk.Entry(frame_auth)
    entry_username.grid(row=0, column=1, pady=2, sticky="ew")
    entry_username.insert(0, data.get("username", ""))
    enable_ctrl_v(entry_username)

    ttk.Label(frame_auth, text="Пароль:").grid(row=1, column=0, sticky="w", pady=2)
    entry_password = ttk.Entry(frame_auth, show="*")
    entry_password.grid(row=1, column=1, pady=2, sticky="ew")
    entry_password.insert(0, data.get("password", ""))
    enable_ctrl_v(entry_password)

    ttk.Label(frame_launch, text="Параметры запуска:").grid(row=0, column=0, sticky="w", pady=2)
    entry_params = ttk.Entry(frame_launch)
    entry_params.grid(row=0, column=1, pady=2, sticky="ew")
    entry_params.insert(0, data.get("parameters", ""))
    enable_ctrl_v(entry_params)

    run_as_admin_var = tk.BooleanVar(value=data.get("run_as_admin", False))

    ttk.Checkbutton(
        frame_launch,
        text="Запуск от имени администратора",
        variable=run_as_admin_var
    ).grid(row=1, column=1, sticky="w", pady=2)

    def save():
        data["name"] = entry_name.get()
        data["platform"] = entry_platform.get()
        data["connect"] = entry_connect.get()
        data["parameters"] = entry_params.get()
        data["run_as_admin"] = run_as_admin_var.get()
        data["interface"] = combo_interface.get()
        data["username"] = entry_username.get()
        data["password"] = entry_password.get()
        data["auth_enterprise"] = {
            "username": entry_username.get(),
            "password": entry_password.get()
        }
        data["last_run"] = entry_last_run.get()
        on_save(data)
        dialog.destroy()

    btn_save = ttk.Button(dialog, text="Сохранить", command=save)
    btn_save.pack(pady=(0, 10))
    
    center_window(master, dialog, 520, 390)


def open_register_dialog(master, on_register):
    dialog = tk.Toplevel(master)
    dialog.title("Создание новой базы")
    dialog.transient(master)
    dialog.grab_set()
    dialog.lift()
    dialog.focus_force()

    data = {
        "type": "file",
        "platform": "",
        "connect": "",
        "parameters": "",
        "interface": "Auto",
        "username": "",
        "password": ""
    }

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    frame_type = ttk.Frame(notebook)
    notebook.add(frame_type, text="1. Тип базы")

    base_type = tk.StringVar(value="file")

    ttk.Radiobutton(frame_type, text="Файловая", variable=base_type, value="file").pack(anchor="w", pady=2)
    ttk.Radiobutton(frame_type, text="Серверная", variable=base_type, value="server").pack(anchor="w", pady=2)
    ttk.Radiobutton(frame_type, text="WS-соединение", variable=base_type, value="ws").pack(anchor="w", pady=2)

    frame_main = ttk.Frame(notebook)
    notebook.add(frame_main, text="2. Сведения")

    ttk.Label(frame_main, text="Наименование:").grid(row=0, column=0, sticky="w", pady=2)
    entry_name = ttk.Entry(frame_main)
    entry_name.grid(row=0, column=1, sticky="ew")
    enable_ctrl_v(entry_name)

    ttk.Label(frame_main, text="Платформа:").grid(row=1, column=0, sticky="w", pady=2)
    versions = get_installed_1c_versions()

    entry_platform = ttk.Combobox(frame_main, values=versions)
    entry_platform.grid(row=1, column=1, sticky="ew")
    if versions:
        entry_platform.set(versions[0])
    enable_ctrl_v(entry_platform)

    ttk.Label(frame_main, text="Строка подключения / ссылка:").grid(row=2, column=0, sticky="w", pady=2)
    entry_connect = ttk.Entry(frame_main)
    entry_connect.grid(row=2, column=1, sticky="ew")
    enable_ctrl_v(entry_connect)

    frame_main.columnconfigure(1, weight=1)

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

    frame_extra.columnconfigure(1, weight=1)

    def save():
        typ = base_type.get()
        connect = entry_connect.get().strip()

        if typ == "file" and not connect.startswith("File="):
            connect = f"File={connect};"
        elif typ == "server" and not connect.startswith("Srvr="):
            connect = f"Srvr={connect};"
        elif typ == "ws" and not connect.startswith("/WS"):
            connect = f"/WS {connect}"

        new_data = {
            "name": entry_name.get(),
            "platform": entry_platform.get(),
            "connect": connect,
            "parameters": entry_params.get(),
            "interface": combo_interface.get(),
            "username": entry_username.get(),
            "password": entry_password.get(),
            "auth_enterprise": {
                "username": entry_username.get(),
                "password": entry_password.get()
            },
            "last_run": ""
        }
        on_register(new_data)
        dialog.destroy()

    btn_save = ttk.Button(dialog, text="Сохранить", command=save)
    btn_save.pack(pady=(0, 10))
    
    center_window(master, dialog, 520, 360)
