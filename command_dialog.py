import tkinter as tk
from tkinter import ttk, messagebox

def enable_ctrl_v(widget):
    def paste_event(event=None):
        try:
            widget.insert(tk.INSERT, widget.clipboard_get())
        except tk.TclError:
            pass
        return "break"

    def on_keypress(event):
        if event.state & 0x4 and event.keycode == 86:
            return paste_event(event)
        return None

    widget.bind("<KeyPress>", on_keypress, add="+")


def open_command_dialog(master, center_window, command_data=None, on_save=None):
    dialog = tk.Toplevel(master)
    dialog.title("Свойства команды")
    dialog.transient(master)
    dialog.grab_set()
    dialog.resizable(False, False)

    center_window(master, dialog, 520, 240)

    data = command_data.copy() if command_data else {}

    name_var = tk.StringVar(value=data.get("name", ""))
    type_var = tk.StringVar(value=data.get("command_type", "program"))
    command_var = tk.StringVar(value=data.get("command", ""))
    parameters_var = tk.StringVar(value=data.get("parameters", ""))
    workdir_var = tk.StringVar(value=data.get("workdir", ""))

    frame = ttk.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Наименование:").grid(row=0, column=0, sticky="w", pady=3)
    entry_name = ttk.Entry(frame, textvariable=name_var)
    entry_name.grid(row=0, column=1, sticky="ew", pady=3)
    enable_ctrl_v(entry_name)
    
    ttk.Label(frame, text="Тип:").grid(row=1, column=0, sticky="w", pady=3)
    
    ttk.Combobox(
        frame,
        textvariable=type_var,
        values=["program", "folder", "document", "script", "url"],
        state="readonly"
    ).grid(row=1, column=1, sticky="ew", pady=3)

    ttk.Label(frame, text="Команда:").grid(row=2, column=0, sticky="w", pady=3)
    entry_command = ttk.Entry(frame, textvariable=command_var)
    entry_command.grid(row=2, column=1, sticky="ew", pady=3)
    enable_ctrl_v(entry_command)

    ttk.Label(frame, text="Параметры:").grid(row=3, column=0, sticky="w", pady=3)
    entry_parameters = ttk.Entry(frame, textvariable=parameters_var)
    entry_parameters.grid(row=3, column=1, sticky="ew", pady=3)
    enable_ctrl_v(entry_parameters)
    
    
    ttk.Label(frame, text="Рабочий каталог:").grid(row=4, column=0, sticky="w", pady=3)
    entry_workdir = ttk.Entry(frame, textvariable=workdir_var)
    entry_workdir.grid(row=4, column=1, sticky="ew", pady=3)
    enable_ctrl_v(entry_workdir)
    
    frame.columnconfigure(1, weight=1)

    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=(0, 10))

    def apply():
        result = {
            "type": "command",
            "name": name_var.get().strip(),
            "command_type": type_var.get().strip(),
            "command": command_var.get().strip(),
            "parameters": parameters_var.get().strip(),
            "workdir": workdir_var.get().strip()
        }

        if not result["name"]:
            messagebox.showinfo("Свойства команды", "Введите наименование.")
            return

        if on_save:
            on_save(result)

        dialog.destroy()

    ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side="right")
    ttk.Button(button_frame, text="Применить", command=apply).pack(side="right", padx=(0, 6))
