@echo off
echo BUILD RELEASE...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

pyinstaller --clean --onedir --noconfirm ^
--name LANP2PChat ^
--add-data "static;static" ^
--hidden-import=backend ^
--hidden-import=backend.server ^
--hidden-import=backend.routes ^
--hidden-import=backend.app ^
--hidden-import=backend.p2p_async ^
--hidden-import=backend.services ^
--hidden-import=backend.utils ^
--hidden-import=backend.state ^
--hidden-import=backend.group_service ^
--hidden-import=backend.direct_service ^
--hidden-import=backend.sync_service ^
--hidden-import=backend.routes_core ^
--hidden-import=backend.routes_groups ^
--hidden-import=backend.routes_direct ^
--hidden-import=backend.routes_ws ^
--hidden-import=async_user_database ^
--hidden-import=async_groups_database ^
--hidden-import=async_direct_database ^
--hidden-import=settings ^
--hidden-import=aiosqlite ^
--hidden-import=websockets ^
--hidden-import=websockets.legacy ^
--hidden-import=websockets.legacy.server ^
--hidden-import=uvicorn ^
--hidden-import=uvicorn.protocols.websockets.websockets_impl ^
--hidden-import=uvicorn.protocols.http.h11_impl ^
--hidden-import=uvicorn.loops.auto ^
--hidden-import=uvicorn.lifespan.on ^
--hidden-import=uvicorn.logging ^
--hidden-import=asyncio ^
--hidden-import=asyncio.windows_events ^
--hidden-import=websocket ^
--hidden-import=webview ^
--hidden-import=psutil ^
--collect-all websockets ^
--collect-all uvicorn ^
--collect-all aiosqlite ^
--collect-all webview ^
main.py

echo DONE
pause