# SREV-225 Interactive File Migration Path Bounds

## Data

Owner files:

```text
Sandboxie/core/svc/InteractiveWire.h
Sandboxie/core/dll/file_copy.c
SandboxiePlus/QSbieAPI/SbieAPI.cpp
```

Reviewed nodes:

```text
MAN_FILE_MIGRATION_REQ
MAN_FILE_MIGRATION_REQ.file_path[256]
File_MigrateFile_GetMode
SbieDll_CallServerQueue
CSbieAPI::GetQueueReq
QString::fromWCharArray(req->file_path)
```

## Schema

`INTERACTIVE_FILE_MIGRATION_PATH_BOUNDS` defines these local contracts:

- `InteractiveWire.h` owns `MAN_FILE_MIGRATION_REQ.file_path` as a fixed
  256-`WCHAR` interactive queue field.
- `file_copy.c` owns the DLL-side producer that serializes `TruePath` into that
  fixed field before crossing the `MANPROXY` queue boundary.
- The producer must not use an unbounded string copy into `file_path[256]`.
- The producer must zero the full request before sending it so padding and
  unused path tail bytes do not leak across the queue boundary.
- The producer must always NUL-terminate `file_path` inside the fixed field.
- The Qt-side consumer may continue to treat `file_path` as a C string because
  containment is enforced by the producer.
- This SREV does not change request ids, queue names, copy-limit policy,
  migration decision semantics, file size handling, Qt request routing, or the
  fixed wire structure layout.

## Topology

```text
File_MigrateFile_GetMode(TruePath, file_size)
  -> MAN_FILE_MIGRATION_REQ.file_path[256]
  -> SbieDll_CallServerQueue("*MANPROXY_session", req, sizeof(req))
  -> QueueServer stores opaque request bytes
  -> CSbieAPI::GetQueueReq
  -> QString::fromWCharArray(req->file_path)
  -> UI file-migration prompt
```

The queue carrier preserves only byte extent. `InteractiveWire.h` defines the
semantic shape layered on top of those bytes, so the DLL producer must serialize
the path as a contained fixed-field C string before the UI reads it.

## Logic Risk

Before this SREV, `File_MigrateFile_GetMode` wrote `TruePath` into
`MAN_FILE_MIGRATION_REQ.file_path[256]` with `wcscpy`. `TruePath` is an NT path
that can exceed 255 characters, while the wire field is fixed size. An oversized
path can overwrite adjacent stack fields or padding before the request is sent
to the interactive queue.

The same producer also sent the full fixed request without clearing it first.
For shorter paths, bytes after the first NUL in `file_path` and any struct
padding could carry stale stack data into the UI queue.

The minimal legal fix is to zero the request, copy at most
`ARRAYSIZE(req.file_path) - 1` characters, and write the terminator inside
`req.file_path`.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/strsafe/nf-strsafe-stringcchcopyw
- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-s-wcscpy-s-mbscpy-s
- https://learn.microsoft.com/en-us/previous-versions/visualstudio/visual-studio-2013/kk6xf663(v=vs.120)

The official references establish the Windows/Visual C++ string-copy shape:
bounded copies include the destination capacity, and unbounded `wcscpy` cannot
prove sufficient destination space. The local owner remains the fixed Sandboxie
wire schema.

## Fix

`File_MigrateFile_GetMode` now zeroes `MAN_FILE_MIGRATION_REQ`, computes the
source path length, caps it to the fixed `file_path` capacity minus one,
copies only that many characters, and writes the NUL terminator inside the
field before calling `SbieDll_CallServerQueue`.

No queue protocol, request id, file-size field, copy-limit policy, prompt
decision, or Qt reply handling changed.

## Acceptance Gate

Source gate:

```bash
bash docs/plan/check-srev-225.sh
python3 docs/plan/check-core-coverage.py
git diff --check
```

Full historical matrix is deferred to the next batch checkpoint or shared
checker/ledger infrastructure change.

Runtime/build gate still required:

- Windows DLL and SandboxiePlus build for `file_copy.c`,
  `InteractiveWire.h`, and `SbieAPI.cpp`.
- File migration prompt smoke with a normal path proving the displayed path and
  copy decision still round-trip.
- Long NT path smoke over 255 characters proving the request does not overflow
  and the UI receives a contained NUL-terminated truncated path.
  Compatibility policy for displaying full long paths can be handled by a
  future variable-length wire revision.
