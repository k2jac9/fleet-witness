"""CI must reject substituted artifacts and incorrectly selected runtimes."""
import copy
import hashlib
from pathlib import Path
import platform
import tempfile
import unittest

try:
    from scripts import ci_runtime
except ImportError:
    ci_runtime = None


class RuntimeIdentityTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(ci_runtime, 'runtime identity verification is missing')
        return ci_runtime

    def test_wrong_archive_is_rejected_before_installation(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.tar'
            path.write_bytes(b'substituted artifact')
            with self.assertRaisesRegex(ValueError, 'digest'):
                module.verify_archive(path, hashlib.sha256(b'accepted artifact').hexdigest())

    def test_accepted_archive_matches_its_digest(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.tar'
            path.write_bytes(b'accepted artifact')
            self.assertEqual(module.verify_archive(path, '616c95900ce04be981fca43546e50ef9f74806697cc6251cf22be3cbd7a09693'),
                             '616c95900ce04be981fca43546e50ef9f74806697cc6251cf22be3cbd7a09693')

    def test_wrong_actual_python_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'version'):
            self.module().runtime_identity('python', '0.0.0')

    def test_actual_executable_is_hashed(self):
        result = self.module().runtime_identity('python', platform.python_version())
        self.assertEqual(result['version'], platform.python_version())
        self.assertTrue(Path(result['executable']).is_absolute())
        self.assertEqual(len(result['executable_sha256']), 64)

    def test_missing_role_is_not_reported_as_complete_matrix(self):
        module = self.module()
        data = module.load_manifest()
        data['lanes'] = [x for x in data['lanes'] if x['role'] != 'upcoming']
        with self.assertRaisesRegex(ValueError, 'roles'):
            module.validate_manifest(data)

    def test_floating_version_and_missing_digest_are_rejected(self):
        module = self.module()
        for field, value in [('version', 'latest'), ('sha256', ''), ('url', 'http://nodejs.org/dist/runtime')]:
            with self.subTest(field=field):
                data = copy.deepcopy(module.load_manifest())
                data['lanes'][0][field] = value
                with self.assertRaises(ValueError):
                    module.validate_manifest(data)

    def test_duplicate_lane_would_collide_evidence_and_is_rejected(self):
        module = self.module()
        data = module.load_manifest()
        data['lanes'].append(copy.deepcopy(data['lanes'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            module.validate_manifest(data)


if __name__ == '__main__':
    unittest.main()
