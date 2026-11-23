import json
import os
import subprocess
import sys
import tempfile
import unittest

from porechop.adapters import ADAPTERS, BARCODE_CONTEXTS, Adapter
from porechop.adapter_config import load_adapters
from porechop.porechop import add_full_barcode_adapter_sets


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, 'porechop-runner.py')


class TestAdapterConfig(unittest.TestCase):
    def run_porechop(self, *args):
        return subprocess.run([sys.executable, RUNNER] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)

    def test_default_export_round_trip_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            config = os.path.join(directory, 'adapters.json')
            exported = self.run_porechop('--write_default_adapters', config)
            self.assertEqual(exported.returncode, 0, exported.stderr)
            loaded, contexts = load_adapters(config)
            self.assertEqual(contexts, BARCODE_CONTEXTS)
            self.assertEqual([(a.name, a.start_sequence, a.end_sequence) for a in loaded],
                             [(a.name, tuple(a.start_sequence) if a.start_sequence else [],
                               tuple(a.end_sequence) if a.end_sequence else []) for a in ADAPTERS])
            fixture = os.path.join(ROOT, 'test', 'test_one_adapter_set.fastq')
            args = ('-i', fixture, '-t', '1', '-v', '0', '--check_reads', '2', '--no_split')
            original = self.run_porechop(*args)
            configured = self.run_porechop(*(args + ('--adapter_file', config)))
            self.assertEqual(original.returncode, 0, original.stderr)
            self.assertEqual(configured.returncode, 0, configured.stderr)
            self.assertEqual(original.stdout, configured.stdout)
            self.assertNotEqual(self.run_porechop('--write_default_adapters', config).returncode, 0)

    def test_custom_adapter_replaces_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            config = os.path.join(directory, 'adapters.json')
            reads = os.path.join(directory, 'reads.fasta')
            adapter = 'AATGTACTTCGTTCAGTTACGTATTGCT'
            payload = 'GCGCGCGCGCGCGCGCGCGCGCGCGCGCGC'
            with open(config, 'w') as stream:
                json.dump({'version': 1, 'barcode_contexts': BARCODE_CONTEXTS, 'adapters': [
                    {'name': 'custom', 'start': {'name': 'custom_start', 'sequence': adapter}}
                ]}, stream)
            with open(reads, 'w') as stream:
                stream.write('>read\n' + adapter + payload + '\n')
            result = self.run_porechop('-i', reads, '--adapter_file', config, '-t', '1',
                                       '-v', '0', '--no_split', '--extra_end_trim', '0')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '>read\n' + payload + '\n')

    def test_default_export_preserves_barcode_output(self):
        with tempfile.TemporaryDirectory() as directory:
            config = os.path.join(directory, 'adapters.json')
            self.assertEqual(self.run_porechop('--write_default_adapters', config).returncode, 0)
            fixture = os.path.join(ROOT, 'test', 'test_barcodes.fastq')
            default_dir = os.path.join(directory, 'default')
            configured_dir = os.path.join(directory, 'configured')
            args = ('-i', fixture, '-t', '1', '-v', '0')
            default = self.run_porechop(*(args + ('-b', default_dir)))
            configured = self.run_porechop(*(args + ('-b', configured_dir,
                                                       '--adapter_file', config)))
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertEqual(configured.returncode, 0, configured.stderr)
            self.assertEqual(sorted(os.listdir(default_dir)), sorted(os.listdir(configured_dir)))
            for name in os.listdir(default_dir):
                with open(os.path.join(default_dir, name), 'rb') as left, \
                     open(os.path.join(configured_dir, name), 'rb') as right:
                    self.assertEqual(left.read(), right.read())

    def test_custom_barcode_is_used_for_full_sequence(self):
        barcode = Adapter('Barcode 1 (reverse)', start_sequence=('BC01_rev', 'ACGT'),
                          end_sequence=('BC01', 'TGCA'))
        contexts = dict(BARCODE_CONTEXTS, native_start_prefix='TTTT', native_end_prefix='CCCC')
        adapters = add_full_barcode_adapter_sets([Adapter('SQK-NSK007'), barcode], contexts)
        self.assertTrue(adapters[-1].start_sequence[1].startswith('TTTTACGT'))
        self.assertTrue(adapters[-1].end_sequence[1].startswith('CCCCTGCA'))

    def test_invalid_config_fails_with_error(self):
        with tempfile.TemporaryDirectory() as directory:
            config = os.path.join(directory, 'adapters.json')
            with open(config, 'w') as stream:
                json.dump({'version': 1, 'barcode_contexts': BARCODE_CONTEXTS, 'adapters': [
                    {'name': 'invalid', 'start': {'name': 'x', 'sequence': 'ACGTX'}}
                ]}, stream)
            result = self.run_porechop('-i', 'unused', '--adapter_file', config)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('sequence must contain only', result.stderr)
