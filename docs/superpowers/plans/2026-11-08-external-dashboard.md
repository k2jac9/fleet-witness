# External dashboard and controlled campaign implementation plan

> Execution: superpowers:executing-plans, inline owner; independent final reviewer.

**Goal:** Run and preserve a bounded scripted adversarial campaign and deploy its
read-only viewer behind HTTPS and a separate owner password.

**Architecture:** Offline campaign -> four allowlisted assets -> pinned Caddy
container -> Cloud Run, with no controller/provider capability. Dedicated identity
and scheduled deletion limit the pilot lifetime.

**Tech stack:** Existing standard-library Python harness, static HTML/JS, Caddy,
Cloud Run and Cloud Tasks. **Spec:** ADR-0011.

**Task:** external-dashboard. **Owner:** primary agent, existing isolated
fleet/controlled-pilot worktree. **Owned paths:** fleet_witness/campaign.py,
tests/test_campaign.py, deploy/dashboard/, scripts/check_dashboard.py, this plan,
docs/adr/0011-managed-read-only-dashboard.md, docs/adr/README.md,
docs/proposals/passive-fleet-observation.md (user-requested research design),
docs/BUILD_STATUS.md, docs/DEPLOY_GCP.md, docs/OPERATIONS.md, docs/SECURITY_POLICY.md.

## Global constraints and review focus

No provider calls or secrets in assets; no live telemetry claims. Preserve all
failed evidence. Keep baseline loopback server unchanged. Only the owner deploys.
Check auth on every asset and method, path encodings/traversal, private-file
absence, source/image identities, expiry failure handling and bounded cloud cost.

- [x] Write failing campaign tests for paired facts, bad effects, duplicate
  effects and output preservation. Implement strict aggregation and packaging.
- [x] Run 32 seeds into a new retained packet; validate summary and representative
  replay; package only four static assets.
- [x] Write HTTP checker first; show failure against unauthenticated server.
  Configure pinned Caddy and test auth, methods, assets and headers locally.
- [x] Full Python/Node tests and independent review; fix findings before deploy.
- [ ] Deploy reviewed digest with dedicated roleless identity, scale limits,
  separate owner password and scheduled deletion; verify external HTTPS.
- [ ] Record results, exact identities, access instructions and limitations.
