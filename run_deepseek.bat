@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo ==========================================
echo   Werewolf DeepSeek 一键启动
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 python，请先安装 Python 3.11+
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] 正在创建虚拟环境 .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
  )
)

echo [2/5] 正在升级 pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul

echo [3/5] 正在安装项目依赖（首次会稍慢）...
".venv\Scripts\python.exe" -m pip install -e ".[llm]"
if errorlevel 1 (
  echo [错误] 依赖安装失败，请检查网络或 Python 环境
  pause
  exit /b 1
)

echo.
set /p DS_KEY=请输入 DeepSeek API Key（sk-...）:
if "%DS_KEY%"=="" (
  echo [错误] API Key 不能为空
  pause
  exit /b 1
)

echo [4/5] 正在写入 .env ...
(
  echo # 基础配置
  echo DEBUG=false
  echo AI_COUNT=6
  echo MAX_ROUNDS=20
  echo.
  echo # LLM 开关
  echo USE_LLM=true
  echo LLM_PROVIDER=deepseek
  echo.
  echo # DeepSeek 配置
  echo DEEPSEEK_API_KEY=%DS_KEY%
  echo DEEPSEEK_BASE_URL=https://api.deepseek.com
  echo DEEPSEEK_MODEL=deepseek-chat
) > ".env"

echo [5/5] 启动游戏...
echo.
".venv\Scripts\python.exe" main.py

echo.
echo 游戏已退出。按任意键关闭窗口...
pause >nul
