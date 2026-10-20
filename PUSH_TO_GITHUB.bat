@echo off
chcp 65001 > nul
cd /d "%~dp0"
title SN TOOL - Push to GitHub (songseyha1003-maker/skdtool.github)
color 0b
cls

echo ========================================================================
echo  🚀 SN TOOL - GITHUB SYNC & PUBLISH
echo  Repository: https://github.com/songseyha1003-maker/skdtool.github
echo ========================================================================
echo.
echo កំពុងដំណើរការ Push កូដ និង Commits ទាំងអស់ឡើងទៅ GitHub...
echo.

git push -u origin main --force

if %ERRORLEVEL% EQU 0 goto :SUCCESS

echo.
echo ========================================================================
echo  ⚠️ ប្រសិនបើវាទាមទារ Password / Token សូមធ្វើតាមជំហានខាងក្រោម៖
echo ========================================================================
echo.
echo  1. បើក Browser ចូលទៅកាន់: https://github.com/settings/tokens/new
echo  2. ធីក (Check) យកប្រអប់ 'repo' រួចចុច 'Generate token'
echo  3. Copy លេខកូដ Token នោះ (ផ្ដើមដោយ ghp_...)
echo.
set /p USER_TOKEN="សូម Paste លេខកូដ Token ចូលទីនេះរួចចុច Enter (ឬចុច Enter ដើម្បីចាកចេញ): "

if "%USER_TOKEN%"=="" goto :DONE

git push -u https://songseyha1003-maker:%USER_TOKEN%@github.com/songseyha1003-maker/skdtool.github.git main --force

if %ERRORLEVEL% EQU 0 goto :SUCCESS

echo.
echo [ERROR] នៅតែមិនអាច Push បាន សូមពិនិត្យមើល Token ម្តងទៀត។
goto :DONE

:SUCCESS
color 0a
echo.
echo ========================================================================
echo  ✅ ជោគជ័យ ១០០%! កូដទាំងអស់ត្រូវបាន Push ឡើងទៅ GitHub រួចរាល់ស្ថាពរ!
echo  Repo: https://github.com/songseyha1003-maker/skdtool.github
echo ========================================================================

:DONE
echo.
pause
