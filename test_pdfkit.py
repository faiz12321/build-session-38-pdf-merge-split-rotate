"""Small fictional fixture tests. No real documents or all-feature guarantee."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from pypdf import PdfReader, PdfWriter
import check38
import make_sample
import pdfkit

TOOL = str(Path(pdfkit.__file__).resolve())


class PdfKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sample = self.root / 'sample'
        make_sample.setup(self.sample)
        self.a, self.b = self.sample / 'contract.pdf', self.sample / 'invoice.pdf'
        self.out = self.root / 'output.pdf'

    def run_tool(self, *args):
        return subprocess.run([sys.executable, TOOL, *map(str, args)], capture_output=True, text=True)

    def snapshot(self, p):
        return p.read_bytes(), p.stat().st_mtime_ns

    def operations(self, out):
        return [('merge', out, self.a, self.b), ('split', self.a, out, '1-2'), ('rotate', self.a, out, '90')]

    def test_count_reports_each_file_and_total(self):
        r = self.run_tool('count', self.a, self.b)
        self.assertEqual(r.returncode, 0); self.assertIn('Total: 5 pages', r.stdout)

    def test_merge_preserves_order_text_geometry_and_rotation(self):
        self.assertEqual(self.run_tool('merge', self.out, self.a, self.b).returncode, 0)
        self.assertEqual(check38.pages(self.out), check38.pages(self.a) + check38.pages(self.b))

    def test_split_selects_requested_labels(self):
        self.assertEqual(self.run_tool('split', self.b, self.out, '2-3').returncode, 0)
        self.assertEqual(check38.pages(self.out), check38.pages(self.b)[1:3])

    def test_split_single_page(self):
        self.assertEqual(self.run_tool('split', self.b, self.out, '2').returncode, 0)
        self.assertEqual(check38.pages(self.out), check38.pages(self.b)[1:2])

    def test_rotate_all_preserves_text_geometry_and_changes_rotation(self):
        self.assertEqual(self.run_tool('rotate', self.a, self.out, '90').returncode, 0)
        self.assertEqual(check38.pages(self.out), [(t, b, (r + 90) % 360) for t, b, r in check38.pages(self.a)])

    def test_rotate_only_selected_page(self):
        self.assertEqual(self.run_tool('rotate', self.b, self.out, '180', '--page', '2').returncode, 0)
        expected = [(t, b, (r + (180 if i == 1 else 0)) % 360) for i, (t, b, r) in enumerate(check38.pages(self.b))]
        self.assertEqual(check38.pages(self.out), expected)

    def test_existing_output_preserves_bytes_and_mtime_for_each_operation(self):
        self.out.write_bytes(b'KEEP PRIVATE DATA'); before = self.snapshot(self.out)
        for args in self.operations(self.out):
            with self.subTest(command=args[0]):
                r = self.run_tool(*args); self.assertEqual(r.returncode, 1)
                self.assertIn('already exists', r.stderr); self.assertEqual(before, self.snapshot(self.out))

    def test_existing_empty_output_is_refused(self):
        self.out.touch(); before = self.snapshot(self.out)
        for args in self.operations(self.out):
            self.assertEqual(self.run_tool(*args).returncode, 1); self.assertEqual(before, self.snapshot(self.out))

    def test_output_equal_to_input_preserves_bytes_and_mtime(self):
        before = self.snapshot(self.a)
        for args in self.operations(self.a):
            self.assertEqual(self.run_tool(*args).returncode, 1); self.assertEqual(before, self.snapshot(self.a))

    def test_relative_alias_of_input_is_refused(self):
        alias = str(self.a.parent / '.' / self.a.name); before = self.snapshot(self.a)
        self.assertEqual(self.run_tool('merge', alias, self.a).returncode, 1)
        self.assertEqual(before, self.snapshot(self.a))

    def test_input_hardlink_output_is_refused(self):
        os.link(self.a, self.out); before = self.snapshot(self.a)
        for args in self.operations(self.out):
            self.assertEqual(self.run_tool(*args).returncode, 1); self.assertEqual(before, self.snapshot(self.a))

    def test_existing_directory_is_refused_without_touching_child(self):
        self.out.mkdir(); child = self.out / 'private'; child.write_bytes(b'KEEP'); before = self.snapshot(child)
        for args in self.operations(self.out):
            self.assertNotEqual(self.run_tool(*args).returncode, 0); self.assertEqual(before, self.snapshot(child))

    def test_symlink_and_dangling_symlink_output_are_refused(self):
        try: self.out.symlink_to(self.a)
        except OSError: self.skipTest('Symlink creation is not available')
        before = self.snapshot(self.a)
        for args in self.operations(self.out):
            self.assertEqual(self.run_tool(*args).returncode, 1); self.assertEqual(before, self.snapshot(self.a))
        self.out.unlink(); target = self.root / 'absent.pdf'; self.out.symlink_to(target)
        for args in self.operations(self.out):
            self.assertEqual(self.run_tool(*args).returncode, 1); self.assertFalse(target.exists()); self.assertTrue(self.out.is_symlink())

    def test_input_bytes_and_mtime_unchanged_after_success(self):
        before = {p: self.snapshot(p) for p in [self.a, self.b]}
        for i, args in enumerate(self.operations(self.out)):
            args = (args[0], *[self.root / ('out%d.pdf' % i) if x == self.out else x for x in args[1:]])
            self.assertEqual(self.run_tool(*args).returncode, 0)
        self.assertEqual(before, {p: self.snapshot(p) for p in before})

    def test_bad_ranges_create_no_output(self):
        for value in ['0', '2-1', '1-99', 'x', '1-', '1-2-3', '-1']:
            with self.subTest(value=value):
                self.assertNotEqual(self.run_tool('split', self.a, self.out, value).returncode, 0)
                self.assertFalse(self.out.exists())

    def test_bad_rotation_or_page_creates_no_output(self):
        for args in [('45',), ('x',), ('90', '--page', '0'), ('90', '--page', '99'), ('90', '--page'), ('90', '--unknown')]:
            self.assertNotEqual(self.run_tool('rotate', self.a, self.out, *args).returncode, 0); self.assertFalse(self.out.exists())

    def test_missing_or_malformed_input_creates_no_output(self):
        bad = self.root / 'bad.pdf'; bad.write_bytes(b'not a PDF')
        for p in [bad, self.root / 'missing.pdf']:
            for args in [('merge', self.out, self.a, p), ('split', p, self.out, '1'), ('rotate', p, self.out, '90')]:
                self.assertNotEqual(self.run_tool(*args).returncode, 0); self.assertFalse(self.out.exists())

    def test_encrypted_input_is_refused(self):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.encrypt('fictional-test-password')
        p = self.root / 'encrypted.pdf'
        with p.open('xb') as h: writer.write(h)
        self.assertEqual(self.run_tool('merge', self.out, p).returncode, 1); self.assertFalse(self.out.exists())

    def test_setup_refuses_existing_folder_and_preserves_nested_data(self):
        p = self.sample / 'nested'; p.mkdir(); child = p / 'keep'; child.write_bytes(b'KEEP'); before = self.snapshot(child)
        with self.assertRaises(FileExistsError): make_sample.setup(self.sample)
        self.assertEqual(before, self.snapshot(child))

    def test_setup_refuses_existing_file_and_preserves_mtime(self):
        p = self.root / 'old'; p.write_bytes(b'KEEP'); before = self.snapshot(p)
        with self.assertRaises(FileExistsError): make_sample.setup(p)
        self.assertEqual(before, self.snapshot(p))

    def test_setup_repeat_preserves_all_generated_files(self):
        before = {p: self.snapshot(p) for p in self.sample.iterdir()}
        with self.assertRaises(FileExistsError): make_sample.setup(self.sample)
        self.assertEqual(before, {p: self.snapshot(p) for p in before})

    def test_fixture_checker_detects_reordered_merged_pages(self):
        sources = [self.sample / (n + '.pdf') for n in ['contract', 'invoice', 'notes']]
        (self.sample / 'sources.sha256.json').write_text(json.dumps({p.name: check38.digest(p) for p in sources}))
        with contextlib.redirect_stdout(io.StringIO()): pdfkit.merge(self.sample / 'merged.pdf', list(reversed(sources)))
        with contextlib.redirect_stdout(io.StringIO()): pdfkit.split(self.a, self.sample / 'first.pdf', '1-2')
        with contextlib.redirect_stdout(io.StringIO()): pdfkit.rotate(sources[-1], self.sample / 'rotated.pdf', 90, None)
        with self.assertRaisesRegex(AssertionError, 'Merged'): check38.verify(self.sample)

    def test_named_pipe_input_is_rejected_without_blocking(self):
        if not hasattr(os, 'mkfifo'): self.skipTest('Named pipes unavailable')
        p = self.root / 'pipe'; os.mkfifo(p)
        r = self.run_tool('merge', self.out, p)
        self.assertEqual(r.returncode, 1); self.assertFalse(self.out.exists())

    def test_serialization_failure_creates_no_destination(self):
        class BrokenWriter:
            def write(self, handle):
                handle.write(b'partial'); raise ValueError('fictional serialization failure')
        with self.assertRaises(ValueError): pdfkit.save_new(BrokenWriter(), self.out)
        self.assertFalse(self.out.exists())

    def test_fixture_success_then_source_digest_tamper_is_detected(self):
        sources = [self.sample / (n + '.pdf') for n in ['contract', 'invoice', 'notes']]
        (self.sample / 'sources.sha256.json').write_text(json.dumps({p.name: check38.digest(p) for p in sources}))
        with contextlib.redirect_stdout(io.StringIO()):
            pdfkit.merge(self.sample / 'merged.pdf', sources)
            pdfkit.split(self.a, self.sample / 'first.pdf', '1-2')
            pdfkit.rotate(sources[-1], self.sample / 'rotated.pdf', 90, None)
            check38.verify(self.sample)
        with self.a.open('ab') as handle: handle.write(b'tampered')
        with self.assertRaisesRegex(AssertionError, 'Source bytes changed'): check38.verify(self.sample)

    def test_setup_cli_refuses_repeat_without_changing_sample(self):
        script = self.root / 'make_sample.py'; script.write_text(Path(make_sample.__file__).read_text())
        before = {p: self.snapshot(p) for p in self.sample.iterdir()}
        r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1); self.assertIn('sample already exists', r.stderr)
        self.assertEqual(before, {p: self.snapshot(p) for p in before})

    def test_manifest_existing_file_preserved(self):
        p = self.sample / 'sources.sha256.json'; p.write_bytes(b'KEEP'); before = self.snapshot(p)
        with self.assertRaises(FileExistsError): check38.snapshot(self.sample)
        self.assertEqual(before, self.snapshot(p))

    def test_manifest_dangling_link_refused(self):
        p = self.sample / 'sources.sha256.json'; target = self.root / 'absent.json'
        try: p.symlink_to(target)
        except OSError: self.skipTest('Symlink creation is not available')
        with self.assertRaises(FileExistsError): check38.snapshot(self.sample)
        self.assertFalse(target.exists()); self.assertTrue(p.is_symlink())

    def test_setup_existing_and_dangling_directory_links_refused(self):
        link = self.root / 'linked'; absent = self.root / 'absent-dir'
        try: link.symlink_to(self.sample, target_is_directory=True)
        except OSError: self.skipTest('Symlink creation is not available')
        before = {p: self.snapshot(p) for p in self.sample.iterdir()}
        with self.assertRaises(FileExistsError): make_sample.setup(link)
        self.assertEqual(before, {p: self.snapshot(p) for p in before})
        link.unlink(); link.symlink_to(absent, target_is_directory=True)
        with self.assertRaises(FileExistsError): make_sample.setup(link)
        self.assertFalse(absent.exists()); self.assertTrue(link.is_symlink())

    def test_help_and_unknown_command(self):
        self.assertEqual(self.run_tool('--help').returncode, 0)
        self.assertNotEqual(self.run_tool('wrong').returncode, 0)
        self.assertNotEqual(self.run_tool().returncode, 0)


if __name__ == '__main__':
    unittest.main()
