# Run this from the root of E:\scripts\xtoys-library after extracting the ZIP there.
# It removes only the experimental repository thumbnail added during testing.
$experimental = ".\images\accelart-maka-albar-soul-eater.jpeg"
if (Test-Path $experimental) {
    Remove-Item $experimental -Force
    Write-Host "Removed experimental thumbnail: $experimental"
}
Write-Host ""
Write-Host "Known-good Python/index files have been restored by extraction."
Write-Host "Now open the xToys Library Manager and DO NOT rebuild the index yet."
Write-Host "First test the player with the restored index.json."
