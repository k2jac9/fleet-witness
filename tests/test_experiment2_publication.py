"""Publication must remove local paths without changing experimental evidence."""
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from test_experiment2_archive import packed

try:
    from scripts import sanitize_experiment2_archive as publication
except ImportError:
    publication = None


class Experiment2PublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(publication, 'publication successor builder is missing')
        self.manifest = {'runtime': {'python_executable': r'C:\Users\fixture\python.exe',
                                     'python_version': '3.12.14'}, 'calls': 2}
        self.files = {'judge/a/manifest.json': json.dumps(self.manifest).encode(),
                      'judge/a/events.jsonl': b'{"cost_usd":0.1}\n',
                      'judge/a/private/requests.jsonl': b'{"request":"retained"}\n',
                      'judge/a/institution.sqlite3': b'SQLite format 3\x00\x80\xff'}

    def make_successor(self, files=None):
        source = packed(files or self.files)
        target = io.BytesIO()
        source_hash = hashlib.sha256(source.getvalue()).hexdigest()
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, 'w') as new:
            publication.write_successor(old, new, source_hash)
        target.seek(0)
        source.seek(0)
        return source, target, source_hash

    def compare(self, source, target, source_hash):
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(target) as new:
            return publication.compare_successor(old, new, source_hash)

    def test_redacts_only_runtime_path_and_preserves_evidence_bytes(self):
        source, target, source_hash = self.make_successor()
        with zipfile.ZipFile(target) as new:
            manifest = json.loads(new.read('experiment2-runs/judge/a/manifest.json'))
            self.assertNotIn('fixture', json.dumps(manifest))
            self.assertEqual(manifest['runtime']['python_version'], '3.12.14')
            self.assertEqual(manifest['calls'], 2)
            for name, raw in self.files.items():
                if not name.endswith('/manifest.json'):
                    self.assertEqual(new.read('experiment2-runs/' + name), raw)
            metadata = json.loads(new.read('experiment2-runs/SANITIZATION.json'))
            self.assertEqual(metadata['source_archive_sha256'], source_hash)
            self.assertEqual(len(metadata['files']), len(self.files) + 3)
            self.assertEqual(sum(row['destination'] is None for row in metadata['files'].values()), 3)
            self.assertNotIn('fixture', json.dumps(metadata))
        result = self.compare(source, target, source_hash)
        self.assertEqual(result['changed_manifests'], 1)
        self.assertEqual(result['unchanged_data_members'], 3)

    def mutate(self, stream, name, value):
        output = io.BytesIO()
        with zipfile.ZipFile(stream) as old, zipfile.ZipFile(output, 'w') as new:
            for item in old.infolist():
                new.writestr(item, value if item.filename == name else old.read(item))
        output.seek(0)
        return output

    def test_detects_changed_receipt_even_if_new_metadata_claims_it(self):
        source, target, source_hash = self.make_successor()
        name = 'judge/a/private/requests.jsonl'
        with zipfile.ZipFile(target) as z:
            metadata = json.loads(z.read('experiment2-runs/SANITIZATION.json'))
        replacement = b'{"request":"different"}\n'
        metadata['files'][name]['published_sha256'] = hashlib.sha256(replacement).hexdigest()
        target = self.mutate(target, 'experiment2-runs/' + name, replacement)
        target = self.mutate(target, 'experiment2-runs/SANITIZATION.json', json.dumps(metadata).encode())
        with self.assertRaises(ValueError):
            self.compare(source, target, source_hash)

    def test_rejects_source_identity_mismatch_in_metadata(self):
        source, target, source_hash = self.make_successor()
        with self.assertRaises(ValueError):
            self.compare(source, target, '0' * 64)

    def test_rejects_missing_or_extra_members(self):
        for name in ('experiment2-runs/extra', '../escape'):
            with self.subTest(name=name):
                source, target, source_hash = self.make_successor()
                with zipfile.ZipFile(target, 'a') as z:
                    z.writestr(name, b'anything')
                with self.assertRaises(ValueError):
                    self.compare(source, target, source_hash)

    def test_rejects_duplicate_successor_members(self):
        source, target, source_hash = self.make_successor()
        with zipfile.ZipFile(target, 'a') as z, self.assertWarns(UserWarning):
            z.writestr('experiment2-runs/judge/a/events.jsonl', b'{}')
        with self.assertRaises(ValueError):
            self.compare(source, target, source_hash)

    def test_rejects_remaining_home_paths_and_private_key_markers(self):
        for value in (b'/home/private-user/key', b'/Users/private-user/key',
                      b'C:\\Users\\private-user\\key', b'\\\\server\\private\\key',
                      b'-----BEGIN PRIVATE KEY-----'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'privacy'):
                    self.make_successor(dict(self.files, **{'judge/a/events.jsonl': value}))

    def test_rejects_duplicate_json_keys_in_manifest(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            self.make_successor(dict(self.files, **{'judge/a/manifest.json': b'{"runtime":{},"runtime":{}}'}))

    def test_preserves_relative_windows_paths_without_treating_them_as_unc(self):
        manifest = dict(self.manifest, output_directory=r'.\runs\judge\f00')
        source, target, source_hash = self.make_successor(
            dict(self.files, **{'judge/a/manifest.json': json.dumps(manifest).encode()}))
        self.assertEqual(self.compare(source, target, source_hash)['changed_manifests'], 1)

    def test_rejects_json_escaped_unc_path(self):
        manifest = dict(self.manifest, output_directory=r'\\private-host\share\run')
        with self.assertRaisesRegex(ValueError, 'privacy'):
            self.make_successor(dict(self.files, **{'judge/a/manifest.json': json.dumps(manifest).encode()}))

    def test_rejects_unverified_original_member(self):
        source = packed(self.files, mutate=lambda m: m.update({'judge/a/events.jsonl': b'changed'}))
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(io.BytesIO(), 'w') as new:
            with self.assertRaisesRegex(ValueError, 'published hash'):
                publication.write_successor(old, new, '0' * 64)

    def test_production_builder_refuses_unpinned_archive_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source.zip', Path(folder) / 'new.zip'
            source.write_bytes(packed(self.files).getvalue())
            with self.assertRaisesRegex(ValueError, 'source archive identity'):
                publication.build(source, target)
            self.assertFalse(target.exists())

    def test_exclusive_output_never_overwrites_existing_file_or_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'archive.zip'
            output.write_bytes(b'keep')
            link = Path(folder) / 'link.zip'
            link.symlink_to(output)
            for path in (output, link):
                with self.subTest(path=path), self.assertRaises(FileExistsError):
                    publication.build(path, path)
                self.assertEqual(output.read_bytes(), b'keep')

    def test_rejects_hidden_zip_comments(self):
        source, target, source_hash = self.make_successor()
        with zipfile.ZipFile(target, 'a') as z:
            z.comment = b'private metadata'
        with self.assertRaisesRegex(ValueError, 'ZIP metadata'):
            self.compare(source, target, source_hash)

    def test_rejects_unlisted_bytes_before_or_after_zip(self):
        for prefix, suffix in ((b'/home/private-user/secret', b''),
                               (b'', b'/home/private-user/secret')):
            with self.subTest(prefix=bool(prefix)):
                source, target, source_hash = self.make_successor()
                altered = io.BytesIO(prefix + target.getvalue() + suffix)
                with self.assertRaises(ValueError):
                    self.compare(source, altered, source_hash)

    def test_rejects_local_only_extra_field(self):
        source, target, source_hash = self.make_successor()
        with zipfile.ZipFile(target) as z:
            item = z.infolist()[0]
            central_offset = z.start_dir
        raw = bytearray(target.getvalue())
        hidden = b'\xfe\xca\x04\x00hide'
        insertion = 30 + len(item.filename.encode('utf-8'))
        struct.pack_into('<H', raw, 28, len(hidden))
        raw[insertion:insertion] = hidden
        # Shift later local offsets and the EOCD central-directory offset,
        # leaving the central extra field empty: ZipFile accepts this archive.
        position = central_offset + len(hidden)
        while raw[position:position+4] == b'PK\x01\x02':
            offset = struct.unpack_from('<I', raw, position+42)[0]
            if offset:
                struct.pack_into('<I', raw, position+42, offset+len(hidden))
            name_len, extra_len, comment_len = struct.unpack_from('<HHH', raw, position+28)
            position += 46 + name_len + extra_len + comment_len
        struct.pack_into('<I', raw, len(raw)-6, central_offset+len(hidden))
        with self.assertRaises(ValueError):
            self.compare(source, io.BytesIO(raw), source_hash)

    def test_rejects_unused_bytes_after_deflate_stream(self):
        source, target, source_hash = self.make_successor()
        with zipfile.ZipFile(target) as z:
            item = z.infolist()[0]
            central_offset = z.start_dir
        raw = bytearray(target.getvalue())
        hidden = b'/home/private-user/secret'
        insertion = 30 + len(item.filename.encode('utf-8')) + item.compress_size
        struct.pack_into('<I', raw, 18, item.compress_size+len(hidden))
        raw[insertion:insertion] = hidden
        position = central_offset + len(hidden)
        while raw[position:position+4] == b'PK\x01\x02':
            offset = struct.unpack_from('<I', raw, position+42)[0]
            if offset:
                struct.pack_into('<I', raw, position+42, offset+len(hidden))
            else:
                struct.pack_into('<I', raw, position+20, item.compress_size+len(hidden))
            name_len, extra_len, comment_len = struct.unpack_from('<HHH', raw, position+28)
            position += 46 + name_len + extra_len + comment_len
        struct.pack_into('<I', raw, len(raw)-6, central_offset+len(hidden))
        with self.assertRaises(ValueError):
            self.compare(source, io.BytesIO(raw), source_hash)


if __name__ == '__main__':
    unittest.main()
