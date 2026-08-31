@echo off
chcp 65001 > nul
cd /d "%~dp0"
title DIAGNOSTYKA - vytyaguvannya adres
set PY=py -3
%PY% --version >nul 2>&1 || set PY=python

echo.
echo ========================================
echo   PEREVIRKA VYTYAGUVANNYA ADRES
echo ========================================
echo.
echo Berem 150 sprav za st.286 KK (DTP z poterpilymy),
echo kachaem teksty i dyvymos, skilky adres znahodytsya.
echo Ce zaimae blyzko 5 hvylyn.
echo.

%PY% src\diag_addr.py 40696 150 > DIAGNOSTYKA_REZULTAT.txt 2>&1

echo.
type DIAGNOSTYKA_REZULTAT.txt
echo.
echo ========================================
echo   Rezultat zbereženo u fayli:
echo   DIAGNOSTYKA_REZULTAT.txt
echo   Nadishlit yogo Claude.
echo ========================================
echo.
pause
