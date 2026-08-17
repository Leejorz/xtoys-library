xToys Library Manager - Backup Fix
=================================

Apply these three files to the current project:

  app/config.py
  app/application.py
  ui/gui.py

Fixes:
- Prevents boolean settings from being treated as filesystem paths during startup.
  This makes the settings patch safe even if an earlier config.json contains an
  invalid boolean in a library directory field.
- Adds an editable Settings window that saves the existing library/GitHub/video
  source settings to config.json.
- Adds SpankBang as an xToys-compatible video source.
- Detects SpankBang URLs of the form:
  https://spankbang.com/67cyo/video/...
  as site=spankbang.com and video_id=67cyo.
- Automatically includes spankbang.com in the supported-site list.

No database migration is included and no funscript files are changed.
