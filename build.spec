import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Данные matplotlib (шрифты, стили, mpl-data) — обязательны для PdfPages
mpl_datas = collect_data_files('matplotlib')

a = Analysis(
    ['1.py'],
    pathex=[],
    binaries=[],
    datas=[
        # customtkinter: темы/шрифты обязательны для UI
        (os.path.join(__import__('sysconfig').get_paths()['purelib'],
                      'customtkinter', 'assets'),
         os.path.join('customtkinter', 'assets')),
        # matplotlib: шрифты и стили
        *mpl_datas,
    ],
    hiddenimports=[
        # numpy.typing — для pandas
        'numpy.typing',
        'numpy._typing',
        # основное
        'customtkinter',
        'pandas',
        'numpy',
        'openpyxl',
        'xlrd',
        # --- matplotlib для PDF-отчёта (явный список только нужного) ---
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.figure',
        'matplotlib.axes',
        'matplotlib.axes._axes',
        'matplotlib.axes._base',
        'matplotlib.axis',
        'matplotlib.backend_bases',
        'matplotlib.backends',
        'matplotlib.backends.backend_agg',      # headless-рендер для use('Agg')
        'matplotlib.backends.backend_pdf',      # PdfPages
        'matplotlib.cbook',
        'matplotlib.collections',
        'matplotlib.colors',
        'matplotlib.colorbar',
        'matplotlib.contour',
        'matplotlib.font_manager',
        'matplotlib.gridspec',
        'matplotlib.image',
        'matplotlib.legend',
        'matplotlib.lines',
        'matplotlib.markers',
        'matplotlib.patches',
        'matplotlib.path',
        'matplotlib.projections',
        'matplotlib.projections.polar',
        'matplotlib.scale',
        'matplotlib.spines',
        'matplotlib.ticker',
        'matplotlib.transforms',
        'matplotlib.tri',
        'matplotlib.type1font',
        'matplotlib.units',
        # зависимости matplotlib
        'PIL',
        'PIL.Image',
        'cycler',
        'kiwisolver',
        'fontTools',
        'pyparsing',
        'contourpy',
        'dateutil',
        'dateutil.rrule',
        'dateutil.tz',
        'unittest',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # matplotlib и PIL УБРАНЫ из excludes — они нужны pdf_report.py
        'scipy', 'IPython', 'notebook', 'pytest',
        'tkinter.test',
        'pandas.tests', 'numpy.tests', 'numpy.f2py',
        'sqlite3', 'test', 'pydoc_data',
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