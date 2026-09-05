# CLAUDE.md — Trinetra-DFIR

This file is read automatically at the start of every session. It is the
single source of truth for this project's architecture, conventions and
boundaries. If anything in a prompt conflicts with this file, this file wins
- flag the conflict instead of silently resolving it.

## What this project is

A multi-vendor DVR/NVR forensic acquisition, recovery and analysis platform
(SIH26150). Full design rationale lives in two documents, both in docs/refs/:
- "Draft 3 Technical Blueprint" - architecture, tech stack, ML model choices
  and why, datasets, compliance and security design.
- "Repo Structure & AI-Agent Build Playbook" (this companion, Draft 3) - file
  layout and the phase-by-phase build sequence.
Always check whether a design question is already answered in one of these
before improvising an answer.

## Three constraints that override any other consideration

1. Fully offline. No runtime network calls, no telemetry, no phone-home
   licensing. If a task seems to need a network call, stop and flag it.
2. CPU-only laptop performance. Prefer the smaller/faster model or the
   classical (non-ML) method whenever it meets the accuracy bar.
3. Legally explainable output, AND format-preserving evidence handling
   [CHANGED, Draft 3]. Anything that could end up referenced in a Section
   63 certificate must be deterministic, reproducible, and free of
   black-box claims. Additionally: the primary evidentiary video file is
   never converted, transcoded, or remuxed anywhere in the acquisition,
   parsing, carving, playback, or AI-analysis path. When in doubt, make
   AI-derived output advisory ("investigative lead") rather than
   authoritative, and log it.

## Architecture invariants - do not violate these

- The evidentiary pipeline (engine1 through engine7, engine10) is
  sequential and deterministic. The AI Analytics lane (engine8) and the
  Integrity/anti-tamper checks are READ-ONLY - they annotate and index the
  case, they never modify, re-hash, or write back into the acquired
  evidence or the parsed file tree.
- [NEW, Draft 3] engine5_playback (formerly engine5_depacketizer) decodes
  original proprietary streams IN-MEMORY ONLY for playback (engine9_ui)
  and frame analysis (engine8_ai). decoder.py must never write a new file
  to the case tree. remuxer.py may only ever be called by
  engine9_ui/export_module.py, and only on explicit investigator action -
  never automatically, never as part of the acquisition/parse/carve/view
  pipeline.
- [NEW, Draft 3] Any file produced by export_module.py is a derivative,
  not evidence. It must get its own independent hash (never inherit or
  imply equivalence with the original evidentiary hash), its own
  audit_log entry explicitly tagged as a non-evidentiary export, and must
  be labeled in every UI/report surface as "convenience copy - not for
  submission as primary evidence."
- [NEW, Draft 3] Any per-channel/per-camera extraction performed by a
  parser plugin (engine3_parsers) must be an exact byte-range copy of the
  original acquired image - never a re-serialized reconstruction - so it
  remains hash-verifiable against the same byte range in the original
  image.
- [NEW, Draft 3] Carved fragments (engine4_carver) are saved exactly as
  scanned - raw elementary streams, never repackaged into a container -
  and must be tagged extraction_type=carved_fragment in engine7_case_db,
  so every downstream surface can render them as "raw/fragment" rather
  than implying an intact structured parse.
- Every engine talks to engine7_case_db/audit_log.py for logging; no
  engine writes to the SQLite DB directly. The audit log is hash-chained
  and append-only - never add an update/delete path to it.
- Every OEM filesystem parser implements the fs_base.py interface. Do not
  special-case a parser's call site in the detector or UI.
- Byte-level offsets/signatures for proprietary filesystems are
  placeholders seeded from public literature until verified against a
  real acquired drive. Keep them in a clearly-named constants module per
  parser, never inline, never presented as verified fact until a real
  drive confirms them.

## Coding conventions

- Python 3.11, type-hinted, one engine = one package under app/.
- The binary-parsing AND video-decoding hot paths (raw sector reads,
  hashing, NAL scanning, and now stream decoding) prefer rust_core/ or a
  memory-safe/well-audited native library (FFmpeg/libVLC/libmpv) via PyO3
  or bindings, not naive Python parsing of untrusted bytes - this is a
  security requirement, not a performance nice-to-have.
- Every new module file gets a matching tests/unit/test_<module>.py in the
  SAME phase it's created. No module ships untested.
- UI (engine9_ui) calls into engines; it never contains business logic.
- Desktop UI is PySide6 + PySide6-Fluent-Widgets, single process. Do not
  introduce Electron, a bundled webview, or any HTTP server for the UI.

## Hard "never do this" list

- Never add a network call, telemetry ping, or auto-update check anywhere.
- Never let engine8 (AI) or the integrity lane write to case evidence,
  hashes, or the parsed file tree.
- [NEW, Draft 3] Never remux, transcode, or convert the primary
  evidentiary video file as part of playback or AI analysis - decode
  in-memory only, via engine5_playback/decoder.py. Any MP4/MKV output
  must go through export_module.py, must be separately hashed, and must
  never be presented as, or substituted for, the original evidentiary
  file.
- [NEW, Draft 3] Never let decoder.py or remuxer.py write into the
  evidentiary case tree - decoding is ephemeral (in-memory) only; export
  output goes into a clearly separate derivatives/ location per case.
- Never claim a Section 63 certificate is self-certifying or
  "court-admissible" in code, comments, docs, or UI copy - it is always an
  expert-ready draft.
- Never fabricate or "helpfully guess" proprietary filesystem byte
  offsets as if verified - mark them as placeholders per the invariant
  above.
- Never start work belonging to a later phase in the build playbook, even
  if it looks like quick, obvious follow-on work.

## Phase discipline

This project is being built phase-by-phase per the Build Playbook. At the
start of a session, state which phase you are in and what its acceptance
criteria are before writing code. At the end of a session, run the
Standard Closeout Prompt before stopping. Do not self-initiate the next
phase.

## If you are unsure

Say so, and point to the specific Blueprint or Playbook section the
question touches, rather than proceeding on a best guess for anything
touching: legal/compliance claims, security boundaries, offline
guarantees, the evidentiary-vs-derivative boundary, or which engine owns
a piece of logic.