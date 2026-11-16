"""Compare fresh SSL contexts with ordinary and isolated Python startup.

Read-only: no network, certificates loaded, environment values dumped, or TLS
settings changed. Root fingerprints identify anchors without printing their
contents. Run on the affected runtime; a clean result elsewhere is not a fix.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys


def probe():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    executable = Path(sys.executable).resolve()
    with executable.open('rb') as handle:
        executable_hash = hashlib.file_digest(handle, 'sha256').hexdigest()
    roots = sorted(hashlib.sha256(cert).hexdigest() for cert in context.get_ca_certs(binary_form=True))
    constructor = ssl.SSLContext.__new__
    code = getattr(constructor, '__code__', None)
    return {
        'python_version': sys.version,
        'python_executable': str(executable), 'python_sha256': executable_hash,
        'openssl_version': ssl.OPENSSL_VERSION,
        'ssl_module': ssl.__file__, 'context_module': ssl.SSLContext.__module__,
        'constructor_source': code.co_filename if code else None,
        'startup_hooks': {name: getattr(sys.modules[name], '__file__', None)
                          for name in ('sitecustomize', 'usercustomize') if name in sys.modules},
        'relevant_environment_names_present': [name for name in (
            'PYTHONPATH', 'PYTHONHOME', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'SSLKEYLOGFILE',
            'OPENSSL_CONF', 'OPENSSL_MODULES', 'LD_PRELOAD', 'LD_LIBRARY_PATH') if name in os.environ],
        'initial_root_count': len(roots), 'initial_root_sha256': roots,
        'check_hostname': context.check_hostname,
        'verify_mode': int(context.verify_mode), 'keylog_configured': context.keylog_filename is not None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    ordinary = probe()
    if args.probe:
        print(json.dumps(ordinary))
        return
    child = subprocess.run([sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), '--probe'],
                           text=True, capture_output=True, check=True, timeout=30)
    isolated = json.loads(child.stdout)
    print(json.dumps({'ordinary': ordinary, 'isolated_without_site': isolated,
                      'same_initial_roots': ordinary['initial_root_sha256'] == isolated['initial_root_sha256'],
                      'limits': 'Python startup isolation only; linked OpenSSL, native loader and OS remain shared.'},
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
