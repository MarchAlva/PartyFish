Write-Host "正在打包 PartyFish..." -ForegroundColor Green

# 定义Python绝对路径
$pythonPath = "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe"

# 检查Python是否安装
if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ 错误: 未找到Python。请先安装Python并检查路径是否正确。" -ForegroundColor Red
    exit 1
}

# 安装requirements.txt中的依赖
Write-Host "正在安装依赖..." -ForegroundColor Yellow
try {
    & $pythonPath -m pip install -r requirements.txt
    Write-Host "✅ 依赖安装完成" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 依赖安装失败，请检查网络连接或requirements.txt文件。" -ForegroundColor Red
    Write-Host "错误详情: $_" -ForegroundColor Red
    exit 1
}

# 执行打包命令
Write-Host "正在执行打包命令..." -ForegroundColor Yellow
try {
    & $pythonPath -m PyInstaller `
        --noconfirm `
        --name "PartyFish" `
        --windowed `
        --icon "666.ico" `
        --add-data "resources;resources" `
        --uac-admin `
        --collect-data rapidocr_onnxruntime `
        --collect-all rapidocr_onnxruntime `
        --collect-all onnxruntime `
        --hidden-import=rapidocr_onnxruntime `
        --hidden-import=onnxruntime `
        --hidden-import=cv2 `
        --hidden-import=numpy `
        --hidden-import=PIL `
        --hidden-import=pynput `
        --hidden-import=ttkbootstrap `
        --hidden-import=mss `
        --hidden-import=yaml `
        --hidden-import=winsound `
        PartyFish.py

    Write-Host "✅ 打包完成！" -ForegroundColor Green
    Write-Host "可执行文件位于 dist/PartyFish/ 目录下" -ForegroundColor Cyan
} catch {
    Write-Host "❌ 错误: 打包失败。" -ForegroundColor Red
    Write-Host "错误详情: $_" -ForegroundColor Red
    exit 1
}