import os
import threading
import traceback


def start(data_dir=None, static_dir=None):
    """
    Android entrypoint.

    Вызывается из Android WebView wrapper через Chaquopy.
    Desktop main.py не трогаем.
    """

    try:
        if data_dir:
            os.environ["LANP2PCHAT_DATA_DIR"] = data_dir

        if static_dir:
            os.environ["LANP2PCHAT_STATIC_DIR"] = static_dir

        import backend

        threading.Thread(
            target=backend.start_background_services,
            daemon=True,
        ).start()

        return "ok"

    except Exception:
        return traceback.format_exc()