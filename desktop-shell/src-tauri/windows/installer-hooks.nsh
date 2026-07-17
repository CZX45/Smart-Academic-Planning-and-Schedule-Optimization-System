!macro NSIS_HOOK_PREINSTALL
  File /oname=$PLUGINSDIR\InstallerProcessCoordination.ps1 "${__FILEDIR__}\..\..\..\..\windows\InstallerProcessCoordination.ps1"
  nsExec::ExecToStack 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\InstallerProcessCoordination.ps1" -InstallRoot "$INSTDIR" -TestMode'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP|MB_OK "SAPSOS is running. Close the application before installing or repairing it."
    Abort
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  File /oname=$PLUGINSDIR\InstallerProcessCoordination.ps1 "${__FILEDIR__}\..\..\..\..\windows\InstallerProcessCoordination.ps1"
  nsExec::ExecToStack 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\InstallerProcessCoordination.ps1" -InstallRoot "$INSTDIR" -TestMode'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP|MB_OK "SAPSOS is running. Close the application before uninstalling it."
    Abort
  ${EndIf}
!macroend
