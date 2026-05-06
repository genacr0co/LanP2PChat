from fastapi import Body

from version import APP_VERSION, APP_NAME

from .app import app
from .updater import check_for_update, download_update_installer


@app.get("/api/update/version")
async def api_update_version():
    return {
        "ok": True,
        "app_name": APP_NAME,
        "current_version": APP_VERSION,
    }


@app.get("/api/update/check")
async def api_update_check():
    return check_for_update()


@app.post("/api/update/download")
async def api_update_download(data: dict = Body(default=None)):
    return download_update_installer()
