# PyInstaller build for the CoinFlow desktop app.
#
#   pip install -r requirements-desktop.txt
#   pyinstaller --noconfirm coinflow.spec
#
# Output: dist/CoinFlow.app (macOS), dist/CoinFlow/CoinFlow.exe (Windows), dist/CoinFlow/CoinFlow (Linux).
# macOS signing: set CODESIGN_IDENTITY to a "Developer ID Application: ..." identity in the keychain.
import os
import sys

sys.path.insert(0, os.path.abspath('.'))
from app.version import __version__  # noqa: E402

datas = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
    ('app/schema.sql', 'app'),
    ('app/schema_postgres.sql', 'app'),
]

a = Analysis(
    ['coinflow_desktop.py'],
    pathex=[],
    datas=datas,
    hiddenimports=[],
    excludes=['psycopg2', 'pytest', 'playwright', 'hypothesis', 'tkinter'],  # not used by the desktop app
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CoinFlow',
    console=False,
    icon='packaging/coinflow.png',
    codesign_identity=os.environ.get('CODESIGN_IDENTITY') or None,
    entitlements_file='packaging/entitlements.plist',
)

coll = COLLECT(exe, a.binaries, a.datas, name='CoinFlow')

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='CoinFlow.app',
        icon='packaging/coinflow.png',
        bundle_identifier='io.github.fernando12filho.coinflow',
        version=__version__,
        info_plist={
            'CFBundleShortVersionString': __version__,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
        },
    )
