# Kean Portal Real-Page QA

This workflow verifies the local browser extension against real Kean Student
Portal pages that you open manually. It does not automate login, navigation,
form submission, registration, add/drop, swap, waitlist action, seat changes,
or portal polling.

## Scope

Supported portal entry:

```text
https://kean-ss.colleague.elluciancloud.com/Student
```

Supported extraction boundary:

```text
https://kean-ss.colleague.elluciancloud.com/Student/*
```

The Chrome/Edge optional permission is host-scoped because browser permissions
work at origin scope, but extraction code still enforces the narrower
`/Student` prefix and configured academic page markers.

## QA Steps

1. Start the local app:

   ```powershell
   .\scripts\windows\Start-Smart-Academic-Planner.ps1
   ```

2. Confirm the local app opens at:

   ```text
   http://localhost:3000
   ```

   If `LOCAL_WEB_PORT` is set for local testing, use the matching supported
   port instead, such as `http://localhost:3001`, `http://localhost:3010`, or
   `http://localhost:3011`.

3. Build the browser extension package:

   ```powershell
   corepack pnpm extension:package
   ```

4. Load the generated extension folder:

   ```text
   dist/extension-unpacked
   ```

5. Open Chrome or Edge.
6. Go to `chrome://extensions` or `edge://extensions`.
7. Enable Developer Mode.
8. Click Load unpacked.
9. Select the generated extension build folder.
10. Open:

    ```text
    https://kean-ss.colleague.elluciancloud.com/Student
    ```

11. Log in manually through Kean's official flow.
12. Open each supported academic page manually, such as transcript,
    MyProgress/degree audit, course catalog, section search, student planning,
    and schedule pages.
13. Click the extension.
14. Click `Start Kean Academic Import` if you are testing guided import, then
    grant the Kean host permission when prompted.
15. On each page, click `Capture current guided page`.
16. Verify detected page type.
17. Verify the diagnostic mode summary:

    - current URL;
    - matched route or page marker;
    - visible tables found;
    - visible row count;
    - extracted academic field count;
    - ignored sensitive field count;
    - warnings.

18. Verify extracted fields in the preview table before import.
19. Confirm import only after reviewing the preview.
20. Return to the local app at `http://localhost:3000`, or the supported
    `LOCAL_WEB_PORT` URL used for this test run.
21. Open Data Import Preview and Data Review.
22. Confirm the imported run is non-official and requires manual review.
23. Report missing selectors, unknown fields, or unexpected page types in a new
    issue or follow-up note.

## Diagnostic Mode Boundary

Diagnostic mode may show metadata needed for selector calibration:

- current URL;
- detected page type;
- matched route/page marker;
- visible tables found;
- row count;
- extracted academic field count;
- ignored sensitive field count;
- warning codes and messages.

Diagnostic mode must not display, export, or store:

- passwords;
- hidden credential fields;
- cookies;
- session tokens;
- SAML, MFA, or CAPTCHA payloads;
- registration form payloads;
- add/drop/swap/waitlist action payloads.

## Updating Selectors Safely

If a real page does not match the current selectors:

1. Do not copy real student data into the repository.
2. Create or update fake HTML fixtures under
   `apps/extension/tests/fixtures`.
3. Add a failing extension test that describes the visible academic field or
   page marker.
4. Update `apps/extension/src/shared/kean.ts` route markers, visible text
   markers, expected fields, or allowed aliases.
5. Keep the optional Kean host permission narrow and keep extraction enforced
   to `/Student/*`.
6. Re-run extension tests:

   ```powershell
   corepack pnpm --filter @sapsos/extension test
   ```

## Safety Notes

Imported data is non-official until reviewed. High-impact academic decisions
must be confirmed with Kean or an advisor. The extension does not log in for
you and does not collect credentials, store cookies, bypass school access
controls, or submit portal forms. The workflow has no automatic registration,
no background polling, no seat reservation, and no seat grabbing.
