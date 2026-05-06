@echo off
setlocal enabledelayedexpansion

cls
echo =====================================
echo        LAN P2P Chat Builder
echo =====================================
echo.

call :progress 5 "Starting build..."

call :progress 10 "Checking icon file..."
if not exist "static\src\assets\logo_gers_new.ico" (
    echo.
    echo ERROR: Icon file not found!
    echo Expected: static\src\assets\logo_gers_new.ico
    echo.
    echo Create .ico from logo_gers_new.png first.
    pause
    exit /b 1
)

call :progress 15 "Cleaning old build files..."
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist LANP2PChat.spec del LANP2PChat.spec

call :progress 25 "Running PyInstaller..."

pyinstaller --clean --onedir --noconfirm --windowed ^
--name LANP2PChat ^
--icon "static\src\assets\logo_gers_new.ico" ^
--add-data "static;static" ^
--hidden-import=backend ^
--hidden-import=backend.server ^
--hidden-import=backend.routes ^
--hidden-import=backend.app ^
--hidden-import=backend.services ^
--hidden-import=backend.utils ^
--hidden-import=backend.state ^
--hidden-import=backend.group_service ^
--hidden-import=backend.direct_service ^
--hidden-import=backend.sync_service ^
--hidden-import=backend.updater ^
--hidden-import=backend.routes_core ^
--hidden-import=backend.routes_groups ^
--hidden-import=backend.routes_direct ^
--hidden-import=backend.routes_update ^
--hidden-import=backend.routes_ws ^
--hidden-import=user_db ^
--hidden-import=user_db.schema ^
--hidden-import=user_db.settings ^
--hidden-import=user_db.profile ^
--hidden-import=groups_db ^
--hidden-import=groups_db.common ^
--hidden-import=groups_db.schema ^
--hidden-import=groups_db.groups ^
--hidden-import=groups_db.messages ^
--hidden-import=groups_db.sync ^
--hidden-import=direct_db ^
--hidden-import=direct_db.common ^
--hidden-import=direct_db.schema ^
--hidden-import=direct_db.chats ^
--hidden-import=direct_db.messages ^
--hidden-import=settings ^
--hidden-import=version ^
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
--hidden-import=webview ^
--hidden-import=webview.platforms.winforms ^
--hidden-import=webview.platforms.edgechromium ^
--hidden-import=psutil ^
--collect-all websockets ^
--collect-all uvicorn ^
--collect-all aiosqlite ^
--exclude-module=webview.platforms.android ^
--exclude-module=android ^
--exclude-module=jnius ^
--exclude-module=plyer ^
main.py

if errorlevel 1 (
    echo.
    echo =====================================
    echo BUILD FAILED
    echo =====================================
    pause
    exit /b 1
)

call :progress 95 "Checking output..."

if not exist "dist\LANP2PChat\LANP2PChat.exe" (
    echo.
    echo ERROR: EXE not found!
    pause
    exit /b 1
)

call :progress 100 "Build complete!"

echo.
echo =====================================
echo DONE
echo EXE: dist\LANP2PChat\LANP2PChat.exe
echo =====================================
echo.
pause
exit /b 0


:progress
set percent=%~1
set message=%~2

set bar=
set /a blocks=%percent% / 5

for /L %%i in (1,1,%blocks%) do set bar=!bar!#

set empty=
set /a emptyBlocks=20 - %blocks%

for /L %%i in (1,1,%emptyBlocks%) do set empty=!empty!-

echo [%percent%%%] [!bar!!empty!] %message%
exit /b