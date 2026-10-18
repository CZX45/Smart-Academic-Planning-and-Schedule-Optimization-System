# GitHub safe-sync provenance — 2026-10-18

The authorized publication branch is `comprehensive-repair-20261018-safe-sync`.
This is an independent-root public snapshot of local source commit
`62c2bff06d8f169cb65af3f1c033bf59d745791c`; the original repository, branch,
full history, private evidence, and generated packages remain intact locally.
Use this branch and its verified remote HEAD for subsequent cloud work.
The owner explicitly authorized this replacement name after GitHub rejected
the original slash-delimited name because the existing `codex` branch occupies
its namespace. That existing branch is retained unchanged.
The public snapshot has no shared ancestry with `main`; do not merge histories
or force-push to resolve that difference.

## Scope and sensitive findings

The pre-publication audit inspected all 47 source commits relative to the
fetched remote main, 884 distinct blobs represented across those commit trees,
commit metadata, and all 389 final tracked paths. Main at the start was
`8e055994e3e4435043c66e9362d9d0ede2365ec3`. The target remote branch did not exist.

Sensitive findings were a personal author email in historical commit metadata,
local usernames and machine paths in reports, private protected-file metadata,
and participant-derived academic capture statistics in historical acceptance
documents. A sanitization commit on top of that history would still expose
the older blobs. The independent-root snapshot excludes those ancestors and
uses a public GitHub noreply author identity.

Only 13 existing documentation files were changed. Paths in public command
records use `<SOURCE_WORKTREE>`, `<ORIGINAL_CHECKOUT>`, `<USERPROFILE>`, and
`<PYTHON_3_14>` placeholders. Original commands and logs remain private locally.
The historical real-source matrix is replaced with a public boundary summary;
this does not upgrade or erase the privately retained historical evidence.
Protected-file hashes, sizes, timestamps, and paths are withheld.

No database, backup, installer, raw portal capture, runtime log, screenshot,
browser cache, or generated test output is included. The tracked icon is an
application asset, and the tracked distribution placeholder is an empty
`.gitkeep`, not an installer. Build/package manifests retain source and artifact
hashes without publishing the packages themselves.

## Reviewed pattern matches

- Academic field names and GPA/credit literals are schemas, parser tests, or
  synthetic samples. The UI sample explicitly identifies itself as sanitized
  local test data, not portal-sourced student data. Test fixtures use mock
  courses, example-domain emails, deterministic UUIDs, or generated rows.
  No fixture or academic value was changed by this sync.
- Secret-like strings in redaction tests are deliberately fabricated failure
  inputs. The test JWT contains a literal dummy signature and is asserted to
  be removed; it is not a real session or credential.
- Example credentials in `.env.example`, Docker development configuration, and
  CI are the existing explicit development-only values. Authentication code
  contains field names, header construction, and redaction regexes, not copied
  user secrets. No private environment file is exported.
- User-path examples in redaction tests and regexes are synthetic matcher
  inputs. Actual machine/user paths in documents were replaced.

The complete final reachable Git history and blobs are scanned again before
push. Detailed raw findings stay local because they contain the material being
excluded. Pattern matching is supplemented with source/provenance review;
matches are not automatically treated as either a leak or an exemption.

## Source and verification preservation

All 376 files outside the 13 changed documents match the source Git blobs
exactly. This includes every product source, test, fixture, dependency/config
file, migration, API schema, and safety control. F01–F20 remain unchanged.
Version validation reports `SAPSOS Local Desktop 0.1.8` consistently.

The 77 original test/check log hashes were revalidated. The historical full
suite records still show 616 unit/integration tests, 58 headless E2E tests, and
25 Rust tests: 699 total. These suites were not rerun for this documentation-only
publication. Five documentation-policy tests were rerun and passed. JSON
parsing, source blob parity, identity validation, and Git whitespace checks
are part of the publication gate. Exact prior commands and outcomes remain in
`../comprehensive-repair-20261018/CHECK_RESULTS.json`; public hashes can be
matched to the private original logs.

Real two-subject Catalog acceptance remains PENDING, the full 116-subject gate
remains locked, and real school/advisor and native Windows acceptance remain
separate from synthetic tests. No application logic or protection was weakened.

## Network scope

Only the designated development branch may be pushed, using a normal push.
No merge, force push, branch deletion, tag, Release, installation, desktop
operation, or formal-database change is authorized by this sync.
Remote verification must compare main and PR #28/#87 before/after, verify the
published HEAD, and compare every file path, mode, Git blob and SHA-256 using a
fresh remote clone with `git fsck --full --strict`. Actions status is reported
separately; unfinished runs are PENDING, never PASS.
