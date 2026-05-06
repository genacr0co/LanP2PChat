import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from version import (
    APP_NAME,
    APP_VERSION,
    YANDEX_UPDATE_FOLDER_PUBLIC_URL,
    UPDATE_MANIFEST_FILE_NAME,
    UPDATE_INSTALLER_FILE_NAME,
)

YANDEX_PUBLIC_DOWNLOAD_API = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
REQUEST_TIMEOUT = 20
DOWNLOAD_TIMEOUT = 120


def _parse_version(value):
    parts = []

    for part in str(value or "").strip().replace("v", "").split("."):
        number = ""

        for ch in part:
            if ch.isdigit():
                number += ch
            else:
                break

        if number == "":
            parts.append(0)
        else:
            parts.append(int(number))

    while len(parts) < 4:
        parts.append(0)

    return tuple(parts[:4])


def is_newer_version(remote_version, local_version=APP_VERSION):
    return _parse_version(remote_version) > _parse_version(local_version)


def _safe_file_name(file_name, fallback):
    file_name = str(file_name or "").strip()

    if not file_name:
        return fallback

    file_name = os.path.basename(file_name)

    if not file_name.lower().endswith(".exe") and fallback.lower().endswith(".exe"):
        return fallback

    return file_name


def _get_yandex_direct_download_url(file_name):
    """
    Получает временную прямую ссылку на файл внутри публичной папки Яндекс Диска.

    В version.py хранится одна ссылка на папку, а не отдельные ссылки на каждый файл.
    Поэтому для каждого файла используем параметр path.
    """
    if not YANDEX_UPDATE_FOLDER_PUBLIC_URL:
        raise RuntimeError("YANDEX_UPDATE_FOLDER_PUBLIC_URL is empty")

    response = requests.get(
        YANDEX_PUBLIC_DOWNLOAD_API,
        params={
            "public_key": YANDEX_UPDATE_FOLDER_PUBLIC_URL,
            "path": f"/{file_name}",
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()
    href = payload.get("href")

    if not href:
        raise RuntimeError("Yandex Disk API did not return direct download href")

    return href


def load_update_manifest():
    direct_url = _get_yandex_direct_download_url(UPDATE_MANIFEST_FILE_NAME)

    response = requests.get(direct_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    manifest = response.json()

    if not isinstance(manifest, dict):
        raise RuntimeError("update_manifest.json must contain JSON object")

    return manifest


def check_for_update():
    try:
        manifest = load_update_manifest()

        latest_version = str(manifest.get("latest_version") or "").strip()
        update_available = bool(latest_version and is_newer_version(latest_version, APP_VERSION))

        installer_file_name = _safe_file_name(
            manifest.get("installer_file_name") or UPDATE_INSTALLER_FILE_NAME,
            UPDATE_INSTALLER_FILE_NAME,
        )

        return {
            "ok": True,
            "app_name": APP_NAME,
            "current_version": APP_VERSION,
            "latest_version": latest_version,
            "update_available": update_available,
            "title": manifest.get("title") or "Доступна новая версия",
            "message": manifest.get("message") or "Можно обновить приложение до новой версии.",
            "mandatory": bool(manifest.get("mandatory")),
            "installer_file_name": installer_file_name,
        }

    except Exception as e:
        return {
            "ok": False,
            "app_name": APP_NAME,
            "current_version": APP_VERSION,
            "latest_version": "",
            "update_available": False,
            "error": str(e),
        }


def _get_download_dir(latest_version):
    safe_version = str(latest_version or "unknown").replace("/", "_").replace("\\", "_")
    path = Path(tempfile.gettempdir()) / "LANP2PChat_Update" / safe_version
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_update_installer():
    check = check_for_update()

    if not check.get("ok"):
        return check

    if not check.get("update_available"):
        return {
            "ok": False,
            "error": "no_update_available",
            "current_version": APP_VERSION,
            "latest_version": check.get("latest_version"),
            "update_available": False,
        }

    installer_file_name = _safe_file_name(
        check.get("installer_file_name") or UPDATE_INSTALLER_FILE_NAME,
        UPDATE_INSTALLER_FILE_NAME,
    )

    try:
        direct_url = _get_yandex_direct_download_url(installer_file_name)
        download_dir = _get_download_dir(check.get("latest_version"))
        installer_path = download_dir / installer_file_name
        tmp_path = download_dir / f"{installer_file_name}.download"

        with requests.get(direct_url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()

            with tmp_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        if not tmp_path.exists() or tmp_path.stat().st_size <= 0:
            raise RuntimeError("Downloaded installer is empty")

        if installer_path.exists():
            installer_path.unlink()

        tmp_path.rename(installer_path)

        return {
            "ok": True,
            "update_available": True,
            "current_version": APP_VERSION,
            "latest_version": check.get("latest_version"),
            "installer_path": str(installer_path),
            "installer_file_name": installer_file_name,
            "size_bytes": installer_path.stat().st_size,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "current_version": APP_VERSION,
            "latest_version": check.get("latest_version"),
            "update_available": True,
        }
