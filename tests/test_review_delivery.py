import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'review_delivery.py'
SPEC = importlib.util.spec_from_file_location('review_delivery', MODULE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'delivery').mkdir()
        self.write('code.py', 'print(1)\n')
        self.write('qa.txt', 'checked\n')
        self.write('delivery/report.txt', 'Findings\n')
        self.plan = {'version': 1, 'sources': ['code.py', 'qa.txt'], 'outputs': [
            {'path': 'delivery/report.txt', 'format': 'text', 'nonempty': True}],
            'delivery_root': 'delivery'}
        self.save_plan()

    def write(self, name, data):
        (self.root / name).write_text(data, encoding='utf-8')

    def save_plan(self):
        self.write('plan.json', json.dumps(self.plan))

    def run_action(self, command='capture', receipt='receipt-v1.json'):
        return audit.run(command, str(self.root), 'plan.json', receipt)

    def test_capture_then_check(self):
        self.assertEqual(self.run_action()['state'], 'ready')
        self.assertEqual(self.run_action('check')['state'], 'ready')

    def test_each_watched_file_invalidates(self):
        for name in ['code.py', 'qa.txt', 'delivery/report.txt', 'plan.json']:
            with self.subTest(name=name):
                original = (self.root / name).read_bytes()
                receipt = 'receipt-' + str(len(name)) + '.json'
                self.run_action(receipt=receipt)
                with (self.root / name).open('ab') as stream:
                    stream.write(b' ')
                with self.assertRaises(audit.Review):
                    self.run_action('check', receipt)
                (self.root / name).write_bytes(original)

    def test_hidden_extra_is_review(self):
        self.write('delivery/.hidden', 'private kit')
        with self.assertRaises(audit.Review):
            self.run_action()

    def test_explicit_extra_is_permitted(self):
        self.write('delivery/notes.txt', 'notes')
        self.plan['allowed_extra_files'] = ['delivery/notes.txt']
        self.save_plan()
        self.run_action()

    def test_missing_output(self):
        (self.root / 'delivery/report.txt').unlink()
        with self.assertRaises(audit.Review):
            self.run_action()

    def test_empty_output(self):
        self.write('delivery/report.txt', '')
        with self.assertRaises(audit.Review):
            self.run_action()

    def test_strict_json(self):
        self.plan['outputs'][0]['format'] = 'json'
        self.save_plan()
        for content in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '{']:
            self.write('delivery/report.txt', content)
            with self.assertRaises(audit.Review):
                self.run_action()

    def test_csv_rules(self):
        self.plan['outputs'][0].update(format='csv', columns=['a', 'b'], minimum_rows=2)
        self.save_plan()
        for content in ['a,a\n1,2\n3,4\n', 'a,b\n1\n', 'a,b\n1,2\n', 'b,a\n1,2\n3,4\n']:
            self.write('delivery/report.txt', content)
            with self.assertRaises(audit.Review):
                self.run_action()
        self.write('delivery/report.txt', 'a,b\n1,2\n3,4\n')
        self.run_action()

    def test_lexical_paths_before_filesystem(self):
        with patch.object(audit.Path, 'resolve', side_effect=AssertionError('filesystem touched')):
            for project, plan in [('https://host/path', 'plan.json'), ('\\\\host\\share', 'plan.json'),
                                  ('/\\host/share', 'plan.json'), ('local', '../plan.json'),
                                  ('local', 'a\\b'), ('local', 'file:x')]:
                with self.assertRaises(audit.InputError):
                    audit.run('capture', project, plan, 'receipt.json')

    def test_overwrite_protection(self):
        self.run_action()
        original = (self.root / 'receipt-v1.json').read_bytes()
        with self.assertRaises(audit.InputError):
            self.run_action()
        self.assertEqual(original, (self.root / 'receipt-v1.json').read_bytes())

    def test_nul_paths_rejected_before_filesystem(self):
        with patch.object(audit.Path, 'resolve', side_effect=AssertionError('filesystem touched')):
            for project, plan, receipt in [('local\x00dir', 'plan.json', 'receipt.json'),
                                          ('local', 'plan\x00.json', 'receipt.json'),
                                          ('local', 'plan.json', 'receipt\x00.json')]:
                with self.assertRaises(audit.InputError):
                    audit.run('capture', project, plan, receipt)
        self.plan['outputs'][0]['path'] = 'delivery/report\x00.txt'
        self.save_plan()
        with self.assertRaises(audit.InputError):
            self.run_action()

    def test_bom_json_and_csv(self):
        self.plan['outputs'][0]['format'] = 'json'
        self.save_plan()
        self.write('delivery/report.txt', '\ufeff{"value":1}')
        self.run_action(receipt='json-receipt.json')
        self.run_action('check', receipt='json-receipt.json')
        self.plan['outputs'][0].update(format='csv', columns=['a', 'b'], minimum_rows=1)
        self.save_plan()
        self.write('delivery/report.txt', '\ufeffa,b\n1,2\n')
        self.run_action(receipt='csv-receipt.json')
        self.run_action('check', receipt='csv-receipt.json')

    def test_capture_detects_change_during_reads(self):
        original = audit.formats
        def changed(root, plan):
            original(root, plan)
            self.write('qa.txt', 'changed during read')
        with patch.object(audit, 'formats', side_effect=changed):
            with self.assertRaises(audit.Review):
                self.run_action()
        self.assertFalse((self.root / 'receipt-v1.json').exists())

    def test_bool_is_not_integer(self):
        for field in ['version', 'minimum_rows']:
            with self.subTest(field=field):
                if field == 'version':
                    self.plan['version'] = True
                else:
                    self.plan['version'] = 1
                    self.plan['outputs'][0].update(format='csv', minimum_rows=True)
                self.save_plan()
                with self.assertRaises(audit.InputError):
                    self.run_action()

    def test_receipt_schema_is_exact(self):
        self.run_action()
        value = json.loads((self.root / 'receipt-v1.json').read_text())
        value['approved'] = True
        self.write('receipt-v1.json', json.dumps(value))
        with self.assertRaises(audit.InputError):
            self.run_action('check')

    def test_receipt_cannot_be_in_delivery(self):
        with self.assertRaises(audit.InputError):
            self.run_action(receipt='delivery/receipt.json')


    def test_json_depth_errors_are_classified_by_role(self):
        # JSON implementations differ in whether valid deep arrays need recursion.
        # Verify each role converts a decoder depth error into its public state.
        self.plan["outputs"][0]["format"] = "json"
        self.save_plan()
        self.write("delivery/report.txt", "{}")
        with patch.object(audit, "strict_json", side_effect=RecursionError("decoder depth")):
            with self.assertRaises(audit.Review):
                audit.formats(self.root, self.plan)
            with self.assertRaises(audit.InputError):
                audit.load_plan(self.root, "plan.json", "receipt-v1.json")
        self.run_action()
        with patch.object(audit, "strict_json", side_effect=RecursionError("decoder depth")):
            with self.assertRaises(audit.InputError):
                audit.receipt_data(self.root, "plan.json", "receipt-v1.json", [])


if __name__ == '__main__':
    unittest.main()
