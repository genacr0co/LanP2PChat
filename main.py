import subprocess
import sys
import time
import requests
import webview
import atexit
import os

from settings import HTTP_PORT


BACKEND_URL = f"http://127.0.0.1:{HTTP_PORT}"
backend_process = None


if os.name == "nt":
    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)
    CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
else:
    CREATE_NO_WINDOW = 0
    DETACHED_PROCESS = 0
    CREATE_NEW_PROCESS_GROUP = 0


def wait_for_backend():
    for _ in range(30):
        try:
            response = requests.get(f"{BACKEND_URL}/api/me", timeout=1)

            if response.status_code == 200:
                return True

        except Exception:
            time.sleep(0.5)

    return False


def is_backend_already_running():
    try:
        response = requests.get(f"{BACKEND_URL}/api/me", timeout=1)
        return response.status_code == 200

    except Exception:
        return False


def start_backend():
    global backend_process

    if is_backend_already_running():
        return

    exe = sys.executable

    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if os.name == "nt":
        kwargs["creationflags"] = CREATE_NO_WINDOW

    backend_process = subprocess.Popen(
        [exe, "--server"],
        **kwargs,
    )


def stop_backend():
    global backend_process

    if backend_process and backend_process.poll() is None:
        try:
            backend_process.terminate()
            backend_process.wait(timeout=3)

        except Exception:
            try:
                backend_process.kill()
            except Exception:
                pass


class NativeApi:
    def install_update(self, installer_path):
        """
        Вызывается из frontend через window.pywebview.api.install_update(path).

        Логика:
        - frontend через backend уже скачал установщик во временную папку;
        - здесь desktop wrapper запускает установщик в тихом режиме;
        - старое приложение закрывается;
        - Inno Setup после установки запускает новую версию через /LAUNCHAPP=1.
        """
        installer_path = str(installer_path or "").strip().strip('"')

        if not installer_path:
            return {
                "ok": False,
                "error": "empty_installer_path",
            }

        if not os.path.exists(installer_path):
            return {
                "ok": False,
                "error": "installer_not_found",
                "installer_path": installer_path,
            }

        if not installer_path.lower().endswith(".exe"):
            return {
                "ok": False,
                "error": "installer_must_be_exe",
                "installer_path": installer_path,
            }

        try:
            args = [
                installer_path,
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/LAUNCHAPP=1",
            ]

            kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "close_fds": True,
            }

            if os.name == "nt":
                kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

            subprocess.Popen(args, **kwargs)

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

        try:
            stop_backend()
        finally:
            os._exit(0)


def show_error_window(message):
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0;
                padding: 24px;
                background: #0f172a;
                color: #e5e7eb;
                font-family: Segoe UI, Arial, sans-serif;
            }}

            .box {{
                max-width: 640px;
                margin: 40px auto;
                padding: 24px;
                border: 1px solid #334155;
                border-radius: 16px;
                background: #111827;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
            }}

            h1 {{
                margin: 0 0 12px;
                font-size: 22px;
                color: #f87171;
            }}

            p {{
                line-height: 1.55;
                font-size: 15px;
                color: #cbd5e1;
            }}

            code {{
                color: #93c5fd;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>LAN P2P Chat</h1>
            <p>{message}</p>
            <p>Проверь, не занят ли порт <code>{HTTP_PORT}</code>, и попробуй перезапустить приложение.</p>
        </div>
    </body>
    </html>
    """

    webview.create_window(
        "LAN P2P Chat — ошибка запуска",
        html=html,
        width=720,
        height=420,
    )

    webview.start()


atexit.register(stop_backend)


if __name__ == "__main__":
    if "--server" in sys.argv:
        import backend

        backend.start_background_services()

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            pass

        sys.exit(0)

    start_backend()

    if not wait_for_backend():
        stop_backend()
        show_error_window("Backend не запустился.")
        sys.exit(1)

    webview.create_window(
        "LAN P2P Chat",
        BACKEND_URL,
        width=950,
        height=700,
        js_api=NativeApi(),
    )

    webview.start()

    stop_backend()
