import json
import os


def load_json_file(path, default):
    """Читает JSON; при отсутствии файла возвращает новый объект по умолчанию."""
    if not os.path.exists(path):
        return default()

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_file(path, data):
    """Атомарно сохраняет JSON, чтобы перезапуск не оставил обрезанный файл."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary_path = f"{path}.tmp"

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary_path, path)
