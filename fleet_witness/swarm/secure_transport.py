"""Explicit operator-bound TLS and private key loading for controlled requests.

These checks protect the boundary from configuration mistakes, not a compromised
trusted host. Nothing here grants model, worker or caller spending authority.
"""
import hashlib
import os
from pathlib import Path
import re
import ssl
import stat
import sys


def validate_profile(profile):
    fields = {'key_file', 'ca_file', 'ca_sha256', 'root_sha256',
              'python_executable', 'python_sha256', 'openssl_version'}
    if not isinstance(profile, dict) or set(profile) != fields:
        raise ValueError('invalid controlled transport profile')
    for name in ('key_file', 'ca_file', 'python_executable'):
        value = profile[name]
        if (not isinstance(value, str) or not 1 <= len(value) <= 4096 or
                '\x00' in value or not Path(value).is_absolute() or
                str(Path(value)) != value or '..' in Path(value).parts):
            raise ValueError('invalid controlled transport path')
    for name in ('ca_sha256', 'python_sha256'):
        if not isinstance(profile[name], str) or not re.fullmatch(r'[0-9a-f]{64}', profile[name]):
            raise ValueError('invalid controlled transport identity')
    roots = profile['root_sha256']
    if (not isinstance(roots, list) or not 1 <= len(roots) <= 16 or
            any(not isinstance(root, str) or not re.fullmatch(r'[0-9a-f]{64}', root) for root in roots)
            or len(set(roots)) != len(roots)):
        raise ValueError('invalid controlled TLS root identities')
    if not isinstance(profile['openssl_version'], str) or not 1 <= len(profile['openssl_version']) <= 128:
        raise ValueError('invalid controlled TLS runtime identity')


def _read_file(path, limit):
    if str(Path(path).resolve()) != path:
        raise ValueError('noncanonical controlled transport file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('controlled transport needs a regular file')
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('controlled transport file exceeds limit')
    return raw


def prepare(profile):
    """Verify exact actual runtime/bundle and construct an explicit root-only context."""
    validate_profile(profile)
    try:
        executable = str(Path(sys.executable).resolve())
        if (executable != profile['python_executable'] or ssl.OPENSSL_VERSION != profile['openssl_version'] or
                hashlib.sha256(_read_file(executable, 128 * 1024 * 1024)).hexdigest() != profile['python_sha256']):
            raise ValueError('controlled runtime identity mismatch')
        bundle = _read_file(profile['ca_file'], 4 * 1024 * 1024)
        if hashlib.sha256(bundle).hexdigest() != profile['ca_sha256']:
            raise ValueError('controlled CA bundle identity mismatch')
        expected = set(profile['root_sha256'])
        found = {}
        for pem in re.findall(br'-----BEGIN CERTIFICATE-----\s+.*?-----END CERTIFICATE-----', bundle, re.S):
            certificate = pem.decode('ascii')
            digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(certificate)).hexdigest()
            if digest in expected:
                found[digest] = certificate
        if set(found) != expected:
            raise ValueError('controlled TLS roots missing')
        # Do not use create_default_context: it can honor SSLKEYLOGFILE. Never
        # load default paths or environment-selected trust alongside these roots.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_verify_locations(cadata='\n'.join(found[root] for root in sorted(found)))
        return context
    except (OSError, UnicodeError, ssl.SSLError):
        raise ValueError('controlled transport preparation failed') from None


def read_key(profile):
    """Load the separately named private file; never fall back to environment keys."""
    validate_profile(profile)
    key_path = Path(profile['key_file'])
    try:
        if str(key_path.parent.resolve()) != str(key_path.parent):
            raise ValueError('credential directory must be canonical')
        parent = os.open(key_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(parent)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError('credential directory must be owner-private')
            fd = os.open(key_path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, 'rb') as handle:
                info = os.fstat(handle.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                        stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                    raise ValueError('credential file must be owner-private and singly linked')
                raw = handle.read(514)
        finally:
            os.close(parent)
        value = raw.removesuffix(b'\n').decode('ascii')
        if not 20 <= len(value) <= 512 or any(not 33 <= ord(char) <= 126 for char in value):
            raise ValueError('credential format refused')
        return value
    except (OSError, UnicodeError):
        raise ValueError('controlled credential unavailable') from None
