# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['cloud_download_v2.py', 'util.py', 'SharedDirectory.py', 'check_list_gui.py'],
             pathex=['D:/Programs/Tsinghua-Tools/cloud_download_gui'],
             binaries=[],
             datas=[('C:/Users/HuXiao/AppData/Local/Programs/Python/Python37/lib/site-packages/ttkwidgets/assets/checked.png', 'imgs'), ('C:/Users/HuXiao/AppData/Local/Programs/Python/Python37/lib/site-packages/ttkwidgets/assets/unchecked.png', 'imgs'), ('C:/Users/HuXiao/AppData/Local/Programs/Python/Python37/lib/site-packages/ttkwidgets/assets/tristate.png', 'imgs')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='cloud_download_v2.1',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          icon='D:/Programs/Tsinghua-Tools/cloud_download_gui/logo.ico')