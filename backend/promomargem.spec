# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — empacota FastAPI backend como diretório standalone.
# Output: dist/promomargem-backend/promomargem-backend.exe (+ DLLs e dados)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['runner.py'],            # entry executavel; chama uvicorn.run(app)
    pathex=[],
    binaries=[],
    datas=collect_data_files('pandas') + collect_data_files('numpy'),
    hiddenimports=[
        'app.main',           # garante que o pacote 'app' entre no bundle
                              # mesmo que runner.py importe tarde (lazy).
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        *collect_submodules('app'),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'IPython', 'jupyter',
        'PIL', 'scipy', 'sklearn', 'pytest', 'notebook',
        'sphinx', 'docutils', 'lxml', 'pyarrow', 'numba',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='promomargem-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # antivírus quarantina UPX-ed binaries
    console=False,            # sem janela de console (preto piscando)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='promomargem-backend',
)
