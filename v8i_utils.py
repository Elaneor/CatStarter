import os


DEFAULT_V8I = os.path.expandvars("%APPDATA%/1C/1CEStart/ibases.v8i")

def normalize_path(path):
    return path.replace("/", "\\").strip()


def parse_v8i_file(path):
    text = None

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(path, "r", encoding=encoding) as f:
                text = f.read()
            break
        except Exception:
            continue

    if text is None:
        raise RuntimeError(f"Не удалось прочитать {path} ни в utf-8-sig, ни в cp1251")

    items = []
    current_name = None
    current_data = {}

    def flush_current():
        nonlocal current_name, current_data

        if current_name is None:
            return

        connect = current_data.get("Connect", "")
        folder = current_data.get("Folder", "")

        if not connect:
            if folder:
                items.append({
                    "type": "group",
                    "name": current_name,
                    "folder": folder,
                    "id": current_data.get("ID", ""),
                    "external": current_data.get("External", "") == "1"
                })

            return

        username = current_data.get("Usr", "")
        password = current_data.get("Pwd", "")

        version = current_data.get("Version", "")
        default_version = current_data.get("DefaultVersion", "")

        items.append({
            "type": "base",
            "name": current_name,
            "id": current_data.get("ID", ""),
            "connect": connect,
            "folder": folder,
            "platform": version or default_version,
            "version": version,
            "default_version": default_version,
            "external": current_data.get("External", "") == "1",
            "username": username,
            "password": password,
            "parameters": current_data.get("AdditionalParameters", ""),
            "app": current_data.get("App", ""),
            "interface": current_data.get("App", "Auto") or "Auto",
            "auth_mode": "manual" if username else "auto",
            "auth_os": current_data.get("WA", "") == "1",
            "auth_enterprise": {
                "username": username,
                "password": password
            },
            "auth_designer": {
                "username": "",
                "password": ""
            },
            "last_run": "",
            "size": ""
        })

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith(";"):
            continue

        if line.startswith("[") and line.endswith("]"):
            flush_current()
            current_name = line[1:-1].strip()
            current_data = {}
            continue

        if current_name is not None and "=" in line:
            key, value = line.split("=", 1)
            current_data[key.strip()] = value.strip()

    flush_current()

    return items

# переименование пустой группы в локальном ibases.v8i
def rename_local_v8i_empty_group(old_name, new_name, parent_folder=""):
    local_v8i = normalize_path(DEFAULT_V8I)

    if not os.path.exists(local_v8i):
        return False

    text = None
    encoding_used = None

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(local_v8i, "r", encoding=encoding) as f:
                text = f.read()
            encoding_used = encoding
            break
        except Exception:
            continue

    if text is None:
        return False

    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    parent_folder = (parent_folder or "").replace("\\", "/").strip("/")

    if not old_name or not new_name:
        return False

    lines = text.splitlines()
    result = []

    in_target = False
    section_name = ""

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            section_name = stripped[1:-1].strip()
            in_target = section_name == old_name

            if in_target:
                result.append(f"[{new_name}]")
            else:
                result.append(line)

            continue

        result.append(line)

    with open(local_v8i, "w", encoding=encoding_used) as f:
        f.write("\n".join(result) + "\n")

    return True


# обновление произвольного поля базы в локальном ibases.v8i
def update_local_v8i_field(connect, field_name, value):
    local_v8i = normalize_path(DEFAULT_V8I)

    if not os.path.exists(local_v8i):
        return False

    text = None
    encoding_used = None

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(local_v8i, "r", encoding=encoding) as f:
                text = f.read()
            encoding_used = encoding
            break
        except Exception:
            continue

    if text is None:
        return False

    target_connect = (connect or "").strip()
    target_field = (field_name or "").strip()

    if not target_connect or not target_field:
        return False

    lines = text.splitlines()
    result = []

    in_target_section = False
    section_has_field = False
    updated = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            if in_target_section and not section_has_field:
                result.append(f"{target_field}={value}")
                updated = True

            in_target_section = False
            section_has_field = False

        if in_target_section and stripped.lower().startswith(target_field.lower() + "="):
            result.append(f"{target_field}={value}")
            section_has_field = True
            updated = True
            continue

        if stripped.lower().startswith("connect="):
            current_connect = stripped.split("=", 1)[1].strip()
            if current_connect == target_connect:
                in_target_section = True

        result.append(line)

    if in_target_section and not section_has_field:
        result.append(f"{target_field}={value}")
        updated = True

    if not updated:
        return False

    with open(local_v8i, "w", encoding=encoding_used) as f:
        f.write("\n".join(result) + "\n")

    return True


# добавление пустой группы в локальный ibases.v8i
def add_local_v8i_empty_group(group_name, parent_folder=""):
    local_v8i = normalize_path(DEFAULT_V8I)

    if not os.path.exists(local_v8i):
        return False

    text = None
    encoding_used = None

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(local_v8i, "r", encoding=encoding) as f:
                text = f.read()
            encoding_used = encoding
            break
        except Exception:
            continue

    if text is None:
        return False

    group_name = (group_name or "").strip()
    parent_folder = (parent_folder or "").replace("\\", "/").strip("/")

    if not group_name:
        return False

    section_name = group_name

    if f"[{section_name}]" in text:
        return False

    if parent_folder:
        folder_value = f"/{parent_folder}"
    else:
        folder_value = "/"

    block = f"\n[{section_name}]\nFolder={folder_value}\n"

    with open(local_v8i, "w", encoding=encoding_used) as f:
        f.write(text.rstrip() + block + "\n")

    return True
    
# переименование группы в локальном ibases.v8i
def update_local_v8i_folder_path(old_folder_path, new_folder_path):
    local_v8i = normalize_path(DEFAULT_V8I)

    if not os.path.exists(local_v8i):
        return 0

    text = None
    encoding_used = None

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(local_v8i, "r", encoding=encoding) as f:
                text = f.read()
            encoding_used = encoding
            break
        except Exception:
            continue

    if text is None:
        return 0

    old_path = (old_folder_path or "").replace("/", "\\").strip("\\")
    new_path = (new_folder_path or "").replace("/", "\\").strip("\\")

    if not old_path or not new_path:
        return 0

    updated_count = 0
    result = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.lower().startswith("folder="):
            folder_value = stripped.split("=", 1)[1].strip()
            normalized_folder = folder_value.replace("/", "\\").strip("\\")

            if normalized_folder == old_path:
                result.append(f"Folder=/{new_path}")
                updated_count += 1
                continue

            if normalized_folder.startswith(old_path + "\\"):
                suffix = normalized_folder[len(old_path):].strip("\\")
                result.append(f"Folder=/{new_path}\\{suffix}")
                updated_count += 1
                continue

        result.append(line)

    if updated_count:
        with open(local_v8i, "w", encoding=encoding_used) as f:
            f.write("\n".join(result) + "\n")

    return updated_count
    
    # удаление пустой группы из локального ibases.v8i
def delete_local_v8i_empty_group(group_name, parent_folder=""):
    local_v8i = normalize_path(DEFAULT_V8I)

    if not os.path.exists(local_v8i):
        return False

    text = None
    encoding_used = None

    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(local_v8i, "r", encoding=encoding) as f:
                text = f.read()
            encoding_used = encoding
            break
        except Exception:
            continue

    if text is None:
        return False

    group_name = (group_name or "").strip()

    if not group_name:
        return False

    lines = text.splitlines()
    result = []

    current_section = []
    current_name = None

    def flush_section():
        if current_name == group_name:
            return

        result.extend(current_section)

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            if current_section:
                flush_section()

            current_section = [line]
            current_name = stripped[1:-1].strip()
        else:
            current_section.append(line)

    if current_section:
        flush_section()

    with open(local_v8i, "w", encoding=encoding_used) as f:
        f.write("\n".join(result).rstrip() + "\n")

    return True
