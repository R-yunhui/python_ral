@echo off
echo ============================================================
echo 毕昇工作流生成器 Web 服务 v0.2.0
echo ============================================================
echo.

REM 检查虚拟环境
if not exist ".venv" (
    echo [错误] 未找到虚拟环境，请先创建并激活虚拟环境
    echo 创建虚拟环境：python -m venv .venv
    echo 激活虚拟环境：.venv\Scripts\Activate.ps1 (PowerShell) 或 .venv\Scripts\activate.bat (CMD)
    pause
    exit /b 1
)

echo [信息] 激活虚拟环境...
call .venv\Scripts\activate.bat

echo [信息] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 FastAPI，正在安装依赖...
    pip install -r requirements.txt
)

echo.
echo [信息] 启动 FastAPI 服务...
echo 访问地址：http://localhost:8000
echo API 文档：http://localhost:8000/docs
echo ============================================================
echo.

cd bisheng_generator
python api.py

pause
