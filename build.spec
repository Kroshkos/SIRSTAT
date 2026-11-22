import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

mpl_datas = collect_data_files('matplotlib')

a = Analysis(
    ['1.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(__import__('sysconfig').get_paths()['purelib'],
                      'customtkinter', 'assets'),
         os.path.join('customtkinter', 'assets')),
        *mpl_datas,
    ],
    hiddenimports=[
        *[m for m in collect_submodules('numpy.typing') if '.tests' not in m],
        *[m for m in collect_submodules('numpy._typing') if '.tests' not in m],
        'customtkinter',
        'pandas',
        'numpy',
        'numpy.typing',
        'openpyxl',
        'xlrd',
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_pdf',
        'matplotlib.backends.backend_agg',
        'matplotlib.font_manager',
        'matplotlib.patches',
        'matplotlib.gridspec',
        'matplotlib.lines',
        'matplotlib.text',
        'matplotlib.transforms',
        'matplotlib.ticker',
        'matplotlib.colors',
        'matplotlib.cbook',
        'matplotlib.figure',
        'matplotlib.axes',
        'matplotlib.axis',
        'matplotlib.legend',
        *[m for m in collect_submodules('matplotlib.backends')],
        *[m for m in collect_submodules('matplotlib') if '.tests' not in m],
        'PIL',
        'PIL.Image',
        'cycler',
        'kiwisolver',
        'fontTools',
        'pyparsing',
        'contourpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'scipy', 'IPython', 'notebook', 'pytest',
        'tkinter.test',
        'pandas.tests', 'numpy.tests', 'numpy.f2py',
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
    console=False,
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