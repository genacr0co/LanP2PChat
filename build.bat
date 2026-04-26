@echo off
echo BUILD RELEASE...

rmdir /s /q build
rmdir /s /q dist
del *.spec

pyinstaller --clean --onedir --noconfirm ^
--name LANP2PChat ^
--add-data "static;static" ^
--hidden-import=backend ^
--hidden-import=backend.server ^
--hidden-import=backend.routes ^
--hidden-import=backend.p2p ^
--hidden-import=backend.services ^
--hidden-import=backend.utils ^
--hidden-import=backend.state ^
--hidden-import=websockets ^
--hidden-import=websockets.legacy ^
--hidden-import=websockets.legacy.server ^
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
--hidden-import=cryptography ^
--collect-all cryptography ^
main.py

echo DONE
pause