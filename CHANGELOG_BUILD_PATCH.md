# xToys Library Manager — Source/Publishing Patch

This patch is based on the current uploaded project.

## Fixes
- Keeps `scripts.eroscripts_url` as the EroScripts page URL.
- Keeps `video_sources.source_url` as the actual video-host URL.
- `index.json` now writes the EroScripts page into `url` instead of the video-host URL.
- Each funscript remains its own index entry; placeholder links are never grouped.
- Known video hostnames are normalized for the xToys index (`spankbang.com` -> `spankbang`, etc.).
- Page 2/source detection now recognizes the major sites already represented by the reference index, including SpankBang, Pornhub, xVideos and xHamster, in addition to the existing configured sources.

## New Publishing Settings
- GitHub destination with configurable repository URL and public raw funscript base URL.
- HTTP PUT file-server destination with configurable upload URL, public base URL, and optional Basic Authentication.
- Main button is now `Publish Library`; it uses the selected destination.
- Existing GitHub workflow remains the default and existing Git origin is preserved.

## Important
- Do not merge scripts merely because they share a placeholder video source.
- The file-server password is stored in `config.json` in this first implementation. If desired, migrate that credential to Windows Credential Manager in a later security pass.
