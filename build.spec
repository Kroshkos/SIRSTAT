# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec для приложения «Обработка микробиологических данных».
# Сборка:  pyinstaller build.spec --noconfirm
# Артефакт: dist/SIRSTAT.app (macOS) / dist/SIRSTAT.exe (Windows)

import os

block_cipher = None

a = Analysis(
    ['1.py'],
    pathex=[],
    binaries=[],
    datas=[
        # customtkinter: темы/шрифты обязательны для UI в собранном виде.
        # PyInstaller не собирает пакетные данные customtkinter автоматически.
        (os.path.join(__import__('sysconfig').get_paths()['purelib'], 'customtkinter', 'assets'),
         os.path.join('customtkinter', 'assets')),
    ],
    hiddenimports=[
        'customtkinter',
        'pandas',
        'numpy',
        'openpyxl',
        # xlrd — нужен для чтения настоящих старых бинарных .xls (engine='xlrd'
        # в load_data). Встроен в exe, чтобы .xls открывались без pip.
        'xlrd',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Максимально облегчаем сборку: всё, что не используется приложением,
    # не попадает в exe — меньше файлов = быстрее запуск (one-dir) и меньше
    # ложных срабатываний антивирусов.
    excludes=[
        'matplotlib', 'scipy', 'IPython', 'notebook', 'pytest',
        'PIL', 'Image', 'tkinter.test',
        'pandas.tests', 'numpy.tests', 'numpy.f2py', 'numpy.typing',
        'sqlite3', 'test', 'unittest', 'pydoc_data',
        'setuptools', 'pkg_resources', 'pip',
        'lxml', 'jinja2', 'pyarrow', 'odf', 'pyxlsb',
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
    name='SIRSTAT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI-приложение: консоль не показываем
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='SIRSTAT',
)

app = BUNDLE(
    coll,
    name='SIRSTAT.app',
    icon=None,
    bundle_identifier='ru.molchanov.microbiology',
)
