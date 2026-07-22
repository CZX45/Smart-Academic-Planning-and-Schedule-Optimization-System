!macro NSIS_HOOK_PREINSTALL
  ; Tauri currentUser defaults to %LOCALAPPDATA%\${PRODUCTNAME}. The product
  ; contract uses the canonical per-user Programs root. Only rewrite that
  ; untouched Tauri default; preserve a valid existing root and let the
  ; coordinator reject foreign, stale, or user-selected roots.
  StrCmp $INSTDIR "$LOCALAPPDATA\${PRODUCTNAME}" sapsos_preinstall_use_canonical_root sapsos_preinstall_root_ready
  sapsos_preinstall_use_canonical_root:
    StrCpy $INSTDIR "$LOCALAPPDATA\Programs\${PRODUCTNAME}"
  sapsos_preinstall_root_ready:
  File /oname=$PLUGINSDIR\InstallerProcessCoordination.ps1 "${__FILEDIR__}\..\..\..\..\windows\InstallerProcessCoordination.ps1"
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\InstallerProcessCoordination.ps1" -InstallRoot "$INSTDIR" -InstallerVersion "${VERSION}" -TimeoutSeconds 45 -TestMode'
  Pop $0
  ${If} $0 != 0
    DetailPrint "preinstall coordination failed with exit code $0"
    IfSilent sapsos_preinstall_silent_failure sapsos_preinstall_interactive_failure
    sapsos_preinstall_interactive_failure:
      ${If} $0 = 10
        MessageBox MB_ICONSTOP|MB_OK "SAPSOS is running. Close the application before installing or repairing it."
      ${ElseIf} $0 = 20
        MessageBox MB_ICONSTOP|MB_OK "SAPSOS installer preflight validation failed. Please close the installer and retry with a valid SAPSOS installer. Diagnostics: $TEMP\SAPSOS\installer-preflight"
      ${ElseIf} $0 = 30
        MessageBox MB_ICONSTOP|MB_OK "Installer preflight could not inspect SAPSOS processes. Please retry. Diagnostics: $TEMP\SAPSOS\installer-preflight"
      ${Else}
        MessageBox MB_ICONSTOP|MB_OK "Installer preflight failed. Please retry. Diagnostics: $TEMP\SAPSOS\installer-preflight"
      ${EndIf}
    sapsos_preinstall_silent_failure:
    SetErrorLevel 1
    Abort
  ${EndIf}
  File /oname=$PLUGINSDIR\Install-Runtime-Payload.ps1 "${__FILEDIR__}\..\..\..\..\windows\Install-Runtime-Payload.ps1"
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\Install-Runtime-Payload.ps1" -InstallRoot "$INSTDIR" -InstallerVersion "${VERSION}" -DiagnosticDirectory "$TEMP\SAPSOS\installer-runtime" -BeginAttempt'
  Pop $0
  ${If} $0 != 0
    DetailPrint "runtime payload attempt initialization failed with exit code $0"
    IfSilent sapsos_payload_begin_silent_failure sapsos_payload_begin_interactive_failure
    sapsos_payload_begin_interactive_failure:
      MessageBox MB_ICONSTOP|MB_OK "SAPSOS could not initialize runtime payload diagnostics. Please retry. Diagnostics: $TEMP\SAPSOS\installer-runtime"
    sapsos_payload_begin_silent_failure:
    SetErrorLevel 1
    Abort
  ${EndIf}
!macroend

!macro NSIS_HOOK_POSTINSTALL
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\Install-Runtime-Payload.ps1" -InstallRoot "$INSTDIR" -PayloadArchivePath "$INSTDIR\runtime-payload.zip" -PayloadMetadataPath "$INSTDIR\runtime-payload-metadata.json" -InstallerVersion "${VERSION}" -DiagnosticDirectory "$TEMP\SAPSOS\installer-runtime"'
  Pop $0
  ${If} $0 != 0
    DetailPrint "runtime payload installation failed with exit code $0"
    IfSilent sapsos_payload_silent_failure sapsos_payload_interactive_failure
    sapsos_payload_interactive_failure:
      MessageBox MB_ICONSTOP|MB_OK "SAPSOS runtime payload installation failed safely. Required runtime files were not skipped. Diagnostics: $TEMP\SAPSOS\installer-runtime"
    sapsos_payload_silent_failure:
    SetErrorLevel 1
    Abort
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  File /oname=$PLUGINSDIR\InstallerProcessCoordination.ps1 "${__FILEDIR__}\..\..\..\..\windows\InstallerProcessCoordination.ps1"
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\InstallerProcessCoordination.ps1" -InstallRoot "$INSTDIR" -InstallerVersion "${VERSION}" -TimeoutSeconds 45 -TestMode'
  Pop $0
  ${If} $0 != 0
    DetailPrint "preuninstall coordination failed with exit code $0"
    IfSilent sapsos_preuninstall_silent_failure sapsos_preuninstall_interactive_failure
    sapsos_preuninstall_interactive_failure:
      ${If} $0 = 10
        MessageBox MB_ICONSTOP|MB_OK "SAPSOS is running. Close the application before uninstalling it."
      ${ElseIf} $0 = 20
        MessageBox MB_ICONSTOP|MB_OK "SAPSOS installer preflight validation failed. Please retry with a valid SAPSOS installation. Diagnostics: $TEMP\SAPSOS\installer-preflight"
      ${ElseIf} $0 = 30
        MessageBox MB_ICONSTOP|MB_OK "Installer preflight could not inspect SAPSOS processes. Please retry. Diagnostics: $TEMP\SAPSOS\installer-preflight"
      ${Else}
        MessageBox MB_ICONSTOP|MB_OK "Installer preflight failed. Please retry. Diagnostics: $TEMP\SAPSOS\installer-preflight"
      ${EndIf}
    sapsos_preuninstall_silent_failure:
    SetErrorLevel 1
    Abort
  ${EndIf}
!macroend
