@echo off
title FormAI Rust Server

echo.
echo ===============================================
echo           FormAI Rust Server
echo ===============================================
echo.

:: Kill any existing processes
echo Stopping existing servers...
taskkill /F /IM formai-rust.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

echo.
echo Building and starting Rust server...
echo.

:: Build and run Rust server
cargo run --release

echo.
echo Server stopped.
pause