# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
playwright_datas, playwright_binaries, playwright_hiddenimports = collect_all('playwright')
a = Analysis(['main.py'], pathex=['.'], binaries=playwright_binaries, datas=playwright_datas, hiddenimports=playwright_hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='xToys Library Manager', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
