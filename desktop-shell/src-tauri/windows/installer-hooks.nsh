!macro NSIS_HOOK_PREINSTALL
  File /oname=$PLUGINSDIR\InstallerProcessCoordination.ps1 "${__FILEDIR__}\..\..\..\..\windows\InstallerProcessCoordination.ps1"
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\InstallerProcessCoordination.ps1" -InstallRoot "$INSTDIR" -TestMode'
  Pop $0
  ${If} $0 != 0
    DetailPrint "preinstall coordination failed with exit code $0"
    IfSilent sapsos_preinstall_silent_failure sapsos_preinstall_interactive_failure
    sapsos_preinstall_interactive_failure:
      MessageBox MB_ICONSTOP|MB_OK "SAPSOS is running. Close the application before installing or repairing it."
    sapsos_preinstall_silent_failure:
    SetErrorLevel 1
    Abort
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  File /oname=$PLUGINSDIR\InstallerProcessCoordination.ps1 "${__FILEDIR__}\..\..\..\..\windows\InstallerProcessCoordination.ps1"
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\InstallerProcessCoordination.ps1" -InstallRoot "$INSTDIR" -TestMode'
  Pop $0
  ${If} $0 != 0
    DetailPrint "preuninstall coordination failed with exit code $0"
    IfSilent sapsos_preuninstall_silent_failure sapsos_preuninstall_interactive_failure
    sapsos_preuninstall_interactive_failure:
      MessageBox MB_ICONSTOP|MB_OK "SAPSOS is running. Close the application before uninstalling it."
    sapsos_preuninstall_silent_failure:
    SetErrorLevel 1
    Abort
  ${EndIf}
!macroend
