"""Actual local TLS and synthetic private files; never real provider credentials."""
import copy
import hashlib
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

try:
    from fleet_witness.swarm import secure_transport as secure
except ImportError:
    secure = None


def runtime_profile(key, ca, roots):
    executable = Path(sys.executable).resolve()
    return {'key_file': str(key), 'ca_file': str(ca),
            'ca_sha256': hashlib.sha256(ca.read_bytes()).hexdigest(),
            'root_sha256': roots, 'python_executable': str(executable),
            'python_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
            'openssl_version': ssl.OPENSSL_VERSION}


class SecureTransportTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(secure, 'controlled private-key and TLS boundary is missing')
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.key = self.root / 'key'
        self.key.write_text('synthetic-key-for-offline-test-only\n')
        self.key.chmod(0o600)
        # This is a synthetic invalid certificate until a test needs actual TLS.
        self.ca = self.root / 'ca.pem'
        self.ca.write_text('not a certificate')
        self.profile = runtime_profile(self.key, self.ca, ['a' * 64])

    def test_private_key_is_read_without_environment_fallback(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'wrong-environment-key'}):
            self.assertEqual(secure.read_key(self.profile), 'synthetic-key-for-offline-test-only')

    def test_public_symlink_hardlink_and_noncanonical_credentials_are_refused(self):
        self.key.chmod(0o644)
        with self.assertRaises(ValueError): secure.read_key(self.profile)
        self.key.chmod(0o600)
        link = self.root / 'link'
        link.symlink_to(self.key)
        with self.assertRaises(ValueError): secure.read_key(dict(self.profile, key_file=str(link)))
        link.unlink(); os.link(self.key, link)
        with self.assertRaises(ValueError): secure.read_key(self.profile)
        link.unlink()
        with self.assertRaises(ValueError):
            secure.read_key(dict(self.profile, key_file=str(self.root / '..' / self.root.name / 'key')))
        self.root.chmod(0o755)
        with self.assertRaises(ValueError): secure.read_key(self.profile)

    def test_invalid_or_oversized_key_never_appears_in_error(self):
        for value in ('', 'short', 'secret\r\nheader: injected', 'x' * 514):
            self.key.write_text(value)
            with self.assertRaises(ValueError) as raised: secure.read_key(self.profile)
            if value: self.assertNotIn(value, str(raised.exception))

    def test_runtime_and_bundle_mismatch_refused_without_reading_key(self):
        for field in ('python_executable', 'python_sha256', 'openssl_version', 'ca_sha256'):
            bad = copy.deepcopy(self.profile)
            bad[field] = '/wrong/runtime' if field == 'python_executable' else '0' * 64
            with self.subTest(field=field), self.assertRaises(ValueError): secure.prepare(bad)
        self.assertEqual(self.key.read_text(), 'synthetic-key-for-offline-test-only\n')

    def test_unknown_fields_and_duplicate_or_missing_roots_refused(self):
        for bad in (dict(self.profile, proxy='http://example.invalid'),
                    dict(self.profile, root_sha256=[]),
                    dict(self.profile, root_sha256=['a' * 64, 'a' * 64]),
                    dict(self.profile, key_file='relative-path')):
            with self.assertRaises(ValueError): secure.validate_profile(bad)

    @unittest.skipUnless(shutil.which('openssl'), 'local TLS fixture generation requires OpenSSL CLI')
    def test_actual_tls_pinned_root_hostname_and_environment_controls(self):
        fixtures = []
        for index in (1, 2):
            cert, key = self.root / f'cert{index}.pem', self.root / f'tls{index}.key'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                            '-keyout', str(key), '-out', str(cert), '-days', '1',
                            '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'],
                           check=True, capture_output=True, timeout=15)
            fixtures.append((cert, key))
        cert, key = fixtures[0]
        digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()
        profile = runtime_profile(self.key, cert, [digest])
        keylog = self.root / 'forbidden-keylog'
        with patch.dict(os.environ, {'SSL_CERT_FILE': str(fixtures[1][0]),
                                    'SSL_CERT_DIR': str(self.root), 'SSLKEYLOGFILE': str(keylog)}):
            context = secure.prepare(profile)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertIsNone(context.keylog_filename)
        self.assertEqual(len(context.get_ca_certs()), 1)

        def handshake(pair, hostname):
            server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server.load_cert_chain(*map(str, pair))
            left, right = socket.socketpair()
            left.settimeout(3); right.settimeout(3)
            def serve():
                try:
                    with server.wrap_socket(right, server_side=True) as stream:
                        stream.sendall(b'OK')
                except ssl.SSLError:
                    right.close()
            thread = threading.Thread(target=serve)
            thread.start()
            try:
                with context.wrap_socket(left, server_hostname=hostname) as stream:
                    return stream.recv(2)
            finally:
                left.close(); thread.join(4)
        self.assertEqual(handshake(fixtures[0], 'localhost'), b'OK')
        with self.assertRaises(ssl.SSLCertVerificationError): handshake(fixtures[1], 'localhost')
        with self.assertRaises(ssl.SSLCertVerificationError): handshake(fixtures[0], 'wrong.invalid')
        self.assertFalse(keylog.exists())
        with self.assertRaises(ValueError): secure.prepare(dict(profile, root_sha256=['0' * 64]))
