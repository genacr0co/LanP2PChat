# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('static', 'static')]
binaries = []
hiddenimports = ['backend', 'backend.server', 'backend.routes', 'backend.app', 'backend.p2p_async', 'backend.services', 'backend.utils', 'backend.state', 'backend.group_service', 'backend.direct_service', 'backend.sync_service', 'backend.routes_core', 'backend.routes_groups', 'backend.routes_direct', 'backend.routes_ws', 'async_user_database', 'async_groups_database', 'async_direct_database', 'settings', 'aiosqlite', 'websockets', 'websockets.legacy', 'websockets.legacy.server', 'uvicorn', 'uvicorn.protocols.websockets.websockets_impl', 'uvicorn.protocols.http.h11_impl', 'uvicorn.loops.auto', 'uvicorn.lifespan.on', 'uvicorn.logging', 'asyncio', 'asyncio.windows_events', 'websocket', 'webview', 'psutil']
tmp_ret = collect_all('websockets')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('uvicorn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aiosqlite')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LANP2PChat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LANP2PChat',
)
