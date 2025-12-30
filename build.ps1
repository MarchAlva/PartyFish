Write-Host "Packing PartyFish..." -ForegroundColor Green

# Define pyinstaller path using virtual environment
$pyinstallerPath = ".venv\Scripts\pyinstaller.exe"

# Execute packaging command
& $pyinstallerPath `
    --noconfirm `
    --name "PartyFish" `
    --console `
    --icon "666.ico" `
    --add-data "resources;resources" `
    --uac-admin `
    --collect-all rapidocr_onnxruntime `
    --collect-all onnxruntime `
    --collect-all pynput `
    --collect-all ttkbootstrap `
    --collect-all mss `
    --collect-all cv2 `
    --collect-all numpy `
    --collect-all PIL `
    --collect-all yaml `
    --collect-all shapely `
    --collect-all pyclipper `
    --collect-all six `
    PartyFish.py

Write-Host "Packing completed!" -ForegroundColor Green
Read-Host "Press any key to continue..."