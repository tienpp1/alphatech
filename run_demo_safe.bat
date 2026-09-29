@echo off
chcp 65001 > nul
cls
echo ===============================================================================
echo   AI BUSINESS OPERATIONS PLATFORM - KICH BAN KHOI DONG DEMO BAO VE
echo   Trang thai: San sang van hanh cuc bo (127.0.0.1:8000)
echo ===============================================================================
echo.
echo [1/3] Kiem tra ket noi cuc bo...
echo [2/3] Tu dong mo trinh duyet sau 3 giay tai: http://127.0.0.1:8000/accounts/login/
start "" "http://127.0.0.1:8000/accounts/login/"
echo.
echo [3/3] Dang khoi chay may chu Django cuc bo (che do toi uu --noreload)...
echo       Nhan [Ctrl + C] tren cua so nay de dung may chu.
echo ===============================================================================
echo.
python -u manage.py runserver 127.0.0.1:8000 --noreload
pause
