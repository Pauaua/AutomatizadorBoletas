# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['SRC/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('SRC/assets/icon.ico', 'src/assets'),
        ('SRC/assets/logo.png', 'src/assets'),
        ('SRC/core', 'src/core'),
    ],
    hiddenimports=[
        'selenium',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.webdriver.common.keys',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'pandas',
        'openpyxl',
        'openpyxl.styles',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Automatizador de Boletas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='SRC/assets/icon.ico',
)
