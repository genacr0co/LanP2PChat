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

    kwargs = {}

    # CREATE_NEW_CONSOLE есть только на Windows
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

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
        print("Backend не запустился")
        input("Нажми Enter...")
        stop_backend()
        sys.exit(1)

    webview.create_window(
        "LAN P2P Chat",
        BACKEND_URL,
        width=950,
        height=700,
    )

    webview.start()

    stop_backend()