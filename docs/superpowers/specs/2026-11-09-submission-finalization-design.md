# Final submission improvements

Task `submission-finalization-20261109`; owner/integrator Alejandro Castellanos,
assisted by Codex. Base: `2ce59d34f92516cfb6666b891a4b35da2b46c9ba`.
The owner accepted the three proposed improvements and requested autonomous work.

Add a standard-library, read-only submission verifier, a real viewer screenshot
and PNG cover, and a three-minute captioned walkthrough using the existing script.
Keep scientific results and experimental source identities frozen. Preserve prior
packages, manifests, failures and rollback assets. No new inference or cloud work.

## Design choices

- A committed verifier replaces the copy/paste-only verification path. It accepts
  the repository package or an extracted package, checks exact allowlisted members,
  bounded regular-file/ZIP inputs, checksums, current provenance identities,
  metadata/abstract agreement and independently recomputed pilot counts/costs.
  It reports consistency, not independent provider authenticity. It never extracts
  an archive, executes bundled code, contacts a network or repairs input files.
- Check the published package in every Python CI lane. Meaningful mutation tests
  must fail for stale source/package bytes, duplicate/unsafe ZIP members, oversized
  or linked input, inconsistent provenance and incorrect pilot aggregates.
- Render existing SVG artwork into a PNG cover. Capture the real local viewer
  with a visible scripted label. Correct its stale solo-entrant footer before
  capture; no application behavior changes.
- Record a captioned 180-second browser walkthrough: mission, build-only evidence,
  revocation/duplicates, recorded live-pilot results and reproducibility. Keep
  synthetic replay and recorded model evidence labeled separately. No claim of
  live cloud availability or new model execution. Use installed Chrome/FFmpeg;
  publish MP4 separately to avoid inflating the portable evidence ZIP.
- Include a standalone verifier and two PNGs in the explicit package allowlist.
  Preserve the previous manuscript and existing PDF bytes. Update metadata and
  links only after the media actually exists and has been reviewed.

A new model study or viewer redesign would require broader review and would not
help this final delivery. The accepted approach is additive presentation and
verification using existing mechanisms. Contact details and form state stay in
an owner-private artifact record, never Git. Submit only after required details
are supplied and a concrete final package exists; retain the confirmation.
