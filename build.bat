@echo off
echo 正在打包 PartyFish...

pyinstaller --noconfirm ^
    --name "PartyFish" ^
    --windowed ^
    --icon "logo.ico" ^
    --add-data "resources;resources" ^
    --collect-data rapidocr_onnxruntime ^
    --collect-all rapidocr_onnxruntime ^
    --collect-all onnxruntime ^
    --hidden-import=rapidocr_onnxruntime ^
    --hidden-import=onnxruntime ^
    --hidden-import=cv2 ^
    --hidden-import=numpy ^
    --hidden-import=PIL ^
    --hidden-import=pynput ^
    --hidden-import=ttkbootstrap ^
    --hidden-import=mss ^
    --hidden-import=yaml ^
    --hidden-import=winsound ^
    --hidden-import=six ^
    --hidden-import=onnx ^
    --hidden-import=wmi ^
    --hidden-import=psutil ^
    PartyFish.py

echo 打包完成！
pause
