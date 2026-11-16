# Local TLS root investigation — 16 November 2026

Follow-up to [issue #18](https://github.com/k2jac9/fleet-witness/issues/18),
starting at `2160a55324404d6bf9d35d5c7f7132607bbe590f`.
The reported Python 3.12.14 environment had one trusted root before loading
the fixture and two afterwards. Its exact executable/OpenSSL/startup-hook
identity is not available in the checked local receipts. No Python 3.12.14
executable was found on PATH or in the checked Nix store package paths.
The owner confirmed during this investigation that the failing run occurred
in another environment, that it is not recoverable right now, and directed a
rerun using the current environment. The workstation probes below are fresh
verification in that selected environment, not a reproduction on the original
host. Historical root attribution remains explicitly unknown.

## Fresh observations

The current executable is Python 3.15.2, SHA-256
`7f7f9b35ee0ca35d3dbd073bd34e37e1364fae5570ab027f20dfbcb5e6787001`,
linked to OpenSSL 3.5.9 (29 September 2026). The separate `openssl` CLI is
3.6.5; it creates test certificates and is not Python's linked TLS library.

Ordinary and `-I -S` startup both construct a client SSL context with zero
trusted roots, hostname checking enabled, required certificate verification,
and no key logging. Ordinary startup loads the Nix module-discovery
`sitecustomize.py`; isolated startup does not. Neither result shows an
additional trust anchor. This does not establish what injected the historical
root or prove that changing Python versions fixed its cause.

All six existing transport tests pass with both startup modes, including the
one-root assertion, successful handshake with the pinned certificate,
alternate-root rejection, wrong-hostname rejection and environmental controls.
Production transport code and every existing test assertion are unchanged.
Both six-test runs and the runtime diagnostic were repeated after the owner's
current-environment direction and passed again. This fulfills the requested
focused rerun without reclassifying the older failure as explained or fixed.

## Capture on the affected environment

Use the failing environment's actual Python executable:

```sh
python -B scripts/diagnose_tls_roots.py
python -B -m unittest discover -s tests -p test_secure_transport.py -v
```

The diagnostic prints exact runtime identities, initial root fingerprints,
constructor/module locations and startup-hook locations. It records only the
names of selected present environment variables, never their values. It loads
no CA files, makes no network request, and does not change TLS configuration.
Retain its output privately until machine-local paths have been reviewed.

For a bounded test with Python site customization excluded, from the repository
root containing the reviewed source:

```sh
python -I -S -B -c 'import sys, runpy; sys.path.insert(0, "."); sys.argv = ["unittest", "discover", "-s", "tests", "-p", "test_secure_transport.py", "-v"]; runpy.run_module("unittest", run_name="__main__")'
```

Python's [`-I` option](https://docs.python.org/3/using/cmdline.html#cmdoption-I)
ignores Python environment variables and excludes user site paths;
[`-S`](https://docs.python.org/3/using/cmdline.html#cmdoption-S) suppresses site
initialization. They do not replace the linked OpenSSL library, native loader
or host. This is Python startup isolation, not a clean OS/container comparison.
The explicit `SSLContext` configuration remains separate from
[`create_default_context`](https://docs.python.org/3/library/ssl.html#ssl.create_default_context),
which can load default roots and enable environment-selected key logging.

If ordinary startup shows an extra root and isolated startup does not, inspect
the reported startup hooks before changing application code. If both show it,
compare the pinned executable, linked OpenSSL and runtime configuration with
a clean environment. Root fingerprints alone do not identify the injecting
component. Keep the failing environment and its original receipts intact.

## Remaining gate

Issue #18 remains open: the historical root's source is unidentified and its
runtime is unavailable at this time. Current-environment focused verification
is complete. After the owner confirmed the temporary storage override, all 399
tests passed on the current host and every pinned Python runtime, with all five
Node lanes also passing. The [local runtime receipt](../../ci/runtime-validation-20261116.json)
records these checks and their environment limits. They do not explain the
historical extra root or substitute for hosted CI acceptance. Production TLS
configuration and all existing transport assertions remain unchanged.
