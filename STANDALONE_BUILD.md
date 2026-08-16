# Standalone Windows Build

Double-click `Build_Standalone.bat` once on Windows. It installs the build dependencies, installs Chromium for EroScripts, builds `xToys Library Manager.exe`, and places the EXE in the project root.

After that, normal use is simply double-clicking `xToys Library Manager.exe`. Python is not needed to run the finished EXE.

Keep the EXE in the project root because the app uses `config.json`, `funscripts`, `storage`, `index.json`, and `.git` for the existing library and GitHub publishing workflow.
