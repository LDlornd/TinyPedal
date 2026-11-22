Unicode true
RequestExecutionLevel user
SetCompressor /SOLID lzma
!include "MUI2.nsh"
!include "x64.nsh"

!ifndef RELEASE_TAG
!define RELEASE_TAG "20261122"
!endif
!ifndef RELEASE_DIR
!error "RELEASE_DIR must point to a prepared release folder"
!endif
!define APP_NAME "TinyPedal LFS"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\TinyPedal-LFS"

Name "${APP_NAME} 中文版"
OutFile "${RELEASE_DIR}\TinyPedal-LFS-${RELEASE_TAG}-windows-x64-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\TinyPedal-LFS"
InstallDirRegKey HKCU "Software\TinyPedal-LFS" "InstallDir"
VIProductVersion "2.53.2.1122"
VIAddVersionKey /LANG=2052 "ProductName" "TinyPedal LFS 中文分发版"
VIAddVersionKey /LANG=2052 "FileDescription" "TinyPedal LFS 安装程序"
VIAddVersionKey /LANG=2052 "FileVersion" "${RELEASE_TAG}"
VIAddVersionKey /LANG=2052 "LegalCopyright" "TinyPedal developers and contributors"

!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "安装 TinyPedal 的 LFS 中文分发版。程序已包含运行库，无需安装 Python。$\r$\n$\r$\n包含赛道地图、雷达、最佳圈差值及扩展、踏板输入的入门预设。$\r$\n$\r$\n安装前请退出正在运行的 TinyPedal。"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\tinypedal.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_RUN_TEXT "启动 TinyPedal LFS"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\使用教程.html"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "打开使用教程（包含 LFS 配置步骤）"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "此安装包仅支持 64 位 Windows。"
    Quit
  ${EndIf}
  SetRegView 64
FunctionEnd

Section "TinyPedal LFS"
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File /r /x settings "${RELEASE_DIR}\TinyPedal\*.*"
  SetOutPath "$INSTDIR\settings"
  SetOverwrite off
  File "${RELEASE_DIR}\TinyPedal\settings\default.json"
  SetOverwrite on
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\tinypedal.exe"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\使用教程.lnk" "$INSTDIR\使用教程.html"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\卸载.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\tinypedal.exe"
  WriteRegStr HKCU "Software\TinyPedal-LFS" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "TinyPedal LFS 中文版"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "2.53.2-lfs-${RELEASE_TAG}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "TinyPedal developers / LFS 中文分支"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\tinypedal.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetRegView 64
  SetShellVarContext current
  !include "${RELEASE_DIR}\uninstall-files.nsh"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\使用教程.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\卸载.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "Software\TinyPedal-LFS"
SectionEnd
