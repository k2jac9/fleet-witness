# Passive fleet observation on owned web surfaces

Status: proposed research design; no public sensor or third-party scan activated.

## Questions and evidence levels

Observe what contacts an explicitly owned test endpoint, what paths it visits,
and how sequences repeat. Separate raw observations, behavioral clusters and
attribution hypotheses. A User-Agent string is a claim; shared IPs, timestamps,
styles or URLs do not prove a common actor, an AI model or fleet membership.
Even cryptographic challenge completion proves control of a key, not ownership
of all traffic that resembles it. Do not label a geographic/IP cluster a fleet.

## Three complementary mechanisms

1. Passive observation: isolated static research pages with synthetic material,
   bounded request metadata and no executable uploads. Log method, route ID,
   coarse time, response class and bounded user-agent claim. Strip query values,
   cookies, authorization, bodies and unexpected headers before persistence.
   If temporary linkage is needed, use rotating keyed address pseudonyms with
   short retention; pseudonymization is not anonymization. Keep raw platform logs
   private with an explicit retention policy before enabling a sensor.
2. Controlled calibration: our own test agents visit the same surface with known
   timing, identities and coordination. Measure false positives/negatives before
   assigning any real-world cluster score. NAT, proxies, ordinary crawlers and
   shared tools are explicit confounders. Simulated agents stay labelled.
3. Voluntary attestation: an opt-in research endpoint accepts a bounded signed
   nonce and declared fleet/member IDs from consenting participants. Verify key
   possession, replay expiry and signatures; expose no callback URL, shell, model
   tool or arbitrary fetch. No unsolicited messages or automatic recruitment.

## Isolation and costs

Place collection in a disposable service/project boundary with no provider key,
controller, internal tools, sensitive documents or privileged service identity.
Publish no traps containing real credentials. Do not exploit visitors, inject
commands into third-party agents, or follow user-supplied URLs. Fixed-size events,
rate/volume/retention limits, egress restrictions, a spend cap and an expiry plan
are prerequisites. Review provider request logging because app-level stripping
alone does not remove URLs already logged by managed ingress.

## Dashboard and experiment design

Add a distinct observation mode with explicit capture window and freshness.
Show request sequences, route transitions, timing distributions and uncertainty,
not an unsupported globe of attributed agents. Preserve a provenance record for
all derived clusters: event IDs, algorithm version, parameters and counterevidence.
Keep scripted replays, known-agent calibration and unknown visitors in separate
views. No traffic is a valid result; never manufacture activity.

Predeclare tests for multi-agent coordination versus independent crawling, shared
network egress, replayed identities, spoofed user agents and deliberate noise.
Compare clustering against known controlled labels. Record abstentions and
false-discovery rates. Before public activation, select an owned URL, complete a
new reviewed ADR with event schema and retention, test abuse/cost controls and
verify sanitization at every persistence layer. This proposal grants no new
network targets or attribution claims.
