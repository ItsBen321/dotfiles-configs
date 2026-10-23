"""Behavioral checks using temporary vaults; no credentials or paid API calls."""
import contextlib
import errno
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/retrieve.py'
spec = importlib.util.spec_from_file_location('retrieve', SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / 'vault with spaces'
        self.cache = self.root / 'cache'
        self.config = self.root / 'config.json'
        self.vault.mkdir()
        for name in r.profiles()['godot']['required']:
            self.write(name, '# ' + Path(name).stem + '\n\nMandatory original guidance.\n')
        self.write('Godot/Physics.md', '---\ntype: rule\napplies_to: [godot, physics]\n---\n# Physics\n\n## Guidance\n\nUse deferred changes for physics collision shapes.\n\nKeep pause timers consistent.\n')

    def write(self, name, text):
        path = self.vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def catalogue(self):
        return r.refresh(self.vault, self.cache)

    def args(self, *rest):
        return ['--config', str(self.config), '--cache-dir', str(self.cache), *rest]

    def test_hash_detects_same_size_edit_with_preserved_mtime(self):
        first, _, _ = self.catalogue()
        path = self.vault / 'Godot/Physics.md'
        info = path.stat()
        path.write_text(path.read_text().replace('physics', 'signals'), encoding='utf-8')
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        second, _, changes = self.catalogue()
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])
        self.assertEqual(changes['updated'], ['Godot/Physics.md'])
        self.assertFalse(self.catalogue()[2]['changed'])

    def test_added_renamed_deleted_notes_and_categories_refresh(self):
        self.catalogue()
        (self.vault / 'Godot/Physics.md').rename(self.vault / 'Godot/Motion.md')
        self.write('New Topic/New Rule.md', '# New rule\n\n## Guidance\n\nNew knowledge.\n')
        catalogue, _, changes = self.catalogue()
        self.assertEqual(changes['deleted'], ['Godot/Physics.md'])
        eligible, _ = r.eligible_and_required(catalogue, 'godot', {}, None, [])
        self.assertIn('New Topic', r.category_tree(catalogue, eligible))
        (self.vault / 'Godot/Motion.md').unlink()
        self.assertIn('Godot/Motion.md', self.catalogue()[2]['deleted'])

    def test_index_descriptions_refresh_unchanged_note(self):
        self.write('INDEX.md', '# Index\n- [[Godot/Physics]] - Collision rules.\n')
        self.assertEqual(self.catalogue()[0]['notes']['Godot/Physics.md']['description'], 'Collision rules.')
        self.write('INDEX.md', '# Index\n- [[Godot/Physics]] - New routing meaning.\n')
        self.assertEqual(self.catalogue()[0]['notes']['Godot/Physics.md']['description'], 'New routing meaning.')

    def test_required_metadata_and_deprecated_notes(self):
        self.write('Team/Rules.md', '---\nretrieval_required: true\n---\n# Team rules\n')
        self.write('Team/Old.md', '---\nstatus: deprecated\n---\n# Old\n')
        r.atomic_json(self.vault / 'vault-retrieval.json', {'required': ['Godot/Physics.md']})
        catalogue, _, _ = self.catalogue()
        eligible, required = r.eligible_and_required(catalogue, 'godot', {}, None, [])
        self.assertIn('Team/Rules.md', required)
        self.assertIn('Godot/Physics.md', required)
        self.assertNotIn('Team/Old.md', eligible)
        with self.assertRaises(r.RetrievalError):
            r.eligible_and_required(catalogue, 'godot', {}, None, ['Team/Old.md'])

    def test_project_notes_are_scoped_and_root_is_required(self):
        for name in ['Project Notes/Space Game.md', 'Project Notes/Space Game Architecture.md', 'Project Notes/Other Game.md']:
            self.write(name, '# ' + Path(name).stem + '\n')
        catalogue, _, _ = self.catalogue()
        eligible, required = r.eligible_and_required(catalogue, 'godot', {}, 'Space Game', [])
        self.assertIn('Project Notes/Space Game.md', required)
        self.assertIn('Project Notes/Space Game Architecture.md', eligible)
        self.assertNotIn('Project Notes/Other Game.md', eligible + required)
        eligible, required = r.eligible_and_required(catalogue, 'godot', {}, None, [])
        self.assertFalse(any(n.startswith('Project Notes/') for n in eligible + required))

    def test_path_escape_and_symlinks_are_rejected(self):
        outside = self.root / 'secret.md'
        outside.write_text('Outside content', encoding='utf-8')
        for name in ['../secret.md', str(outside), '.hidden.md', 'Godot\\Physics.md']:
            with self.subTest(name=name), self.assertRaises(r.RetrievalError):
                r.note_path(self.vault, name)
        self.write('.hidden.md', '# Hidden\n')
        try:
            (self.vault / 'link.md').symlink_to(outside)
        except OSError:
            self.skipTest('Platform does not allow symlink creation')
        with self.assertRaises(r.RetrievalError):
            r.note_path(self.vault, 'link.md')
        _, text, _ = self.catalogue()
        self.assertNotIn('link.md', text)
        self.assertNotIn('.hidden.md', text)

    def test_output_contains_full_required_and_exact_original_passages(self):
        catalogue, text, _ = self.catalogue()
        _, required = r.eligible_and_required(catalogue, 'godot', {}, None, [])
        output, full, returned, _ = r.render(text, required, ['Godot/Physics.md'], 'deferred collision shapes', 3000, self.root / 'full.md')
        self.assertLessEqual(len(output), 3000)
        for name in required:
            self.assertIn(text[name].rstrip(), output)
        self.assertIn(text['Godot/Physics.md'].rstrip(), full)
        self.assertEqual(returned, ['Godot/Physics.md'])
        for line, end, passage in re.findall(r'\[lines (\d+)-(\d+)\]\n(.*?)(?=\n\[lines|\nReturned|\Z)', output, re.S):
            original = '\n'.join(text['Godot/Physics.md'].splitlines()[int(line)-1:int(end)])
            self.assertTrue(original.startswith(passage.rstrip()))
        with self.assertRaises(r.RetrievalError):
            r.render(text, required, [], 'collision', 100, self.root / 'full.md')

    def test_many_selected_notes_stay_within_budget(self):
        text = {'INDEX.md': '# Index\n'}
        selected = []
        for i in range(24):
            name = f'Note {i}.md'
            selected.append(name)
            text[name] = '# Topic\n\n## Guidance\n\n' + ('Collision rule.\n' * 400)
        output, full, returned, omitted = r.render(text, ['INDEX.md'], selected, 'collision', 3000, self.root / 'full.md')
        self.assertLessEqual(len(output), 3000)
        self.assertEqual(len(returned) + len(omitted), 24)
        self.assertTrue(omitted)
        self.assertIn(text[selected[-1]].rstrip(), full)

    def test_oversized_required_content_fails_before_paid_lookup(self):
        self.write('INDEX.md', '# Index\n' + ('Mandatory line.\n' * 300))
        with patch.object(r, 'evaluate') as api, self.assertRaises(r.RetrievalError):
            r.main(self.args('retrieve', '--profile', 'godot', '--vault', str(self.vault), '--task', 'physics', '--max-chars', '1000'))
        api.assert_not_called()

    def test_default_budget_expands_for_full_large_project_note(self):
        original = '# Space Game\n\n' + ('Mandatory project history.\n' * 2000)
        self.write('Project Notes/Space Game.md', original)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            r.main(self.args('retrieve', '--profile', 'godot', '--vault', str(self.vault),
                             '--project', 'Space Game', '--task', 'physics', '--offline'))
        metadata = json.loads(stderr.getvalue())
        self.assertGreater(metadata['max_chars'], 28000)
        self.assertIn(original.rstrip(), stdout.getvalue())
        self.assertLessEqual(len(stdout.getvalue()), metadata['max_chars'])
        # An explicit limit still fails before incurring API usage.
        with patch.object(r, 'evaluate') as api, self.assertRaises(r.RetrievalError):
            r.main(self.args('retrieve', '--profile', 'godot', '--vault', str(self.vault),
                             '--project', 'Space Game', '--task', 'physics', '--max-chars', '28000'))
        api.assert_not_called()

    def test_default_cache_falls_back_on_read_only_mount(self):
        blocked = self.root / 'read-only-cache'
        real_mkstemp = r.tempfile.mkstemp
        def simulate_mount(*args, **kwargs):
            if Path(kwargs.get('dir', '')) == blocked:
                raise OSError(errno.EROFS, 'Read-only file system')
            return real_mkstemp(*args, **kwargs)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(r, 'local_paths', return_value=(self.config, blocked)), \
                patch.object(r.tempfile, 'mkstemp', side_effect=simulate_mount), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            r.main(['retrieve', '--profile', 'godot', '--vault', str(self.vault),
                    '--task', 'physics', '--offline'])
        metadata = json.loads(stderr.getvalue())
        fallback = Path(metadata['cache_dir'])
        self.addCleanup(r.shutil.rmtree, fallback)
        self.assertTrue(metadata['cache_fallback'])
        self.assertNotEqual(fallback, blocked)
        self.assertTrue(Path(metadata['result']).is_file())
        self.assertIn('Physics.md', stdout.getvalue())
        if sys.platform != 'win32':
            self.assertEqual(fallback.stat().st_mode & 0o777, 0o700)

    def test_explicit_unwritable_cache_is_not_silently_replaced(self):
        with patch.object(r.tempfile, 'mkstemp', side_effect=PermissionError(errno.EACCES, 'Denied')), \
                patch.object(r.tempfile, 'mkdtemp') as fallback, self.assertRaises(r.RetrievalError):
            r.writable_cache(self.cache, explicit=True)
        fallback.assert_not_called()

    def test_unrelated_cache_errors_do_not_trigger_fallback(self):
        with patch.object(r.tempfile, 'mkstemp', side_effect=OSError(errno.ENOSPC, 'Full')), \
                patch.object(r.tempfile, 'mkdtemp') as fallback, self.assertRaises(r.RetrievalError):
            r.writable_cache(self.cache)
        fallback.assert_not_called()

    def test_disable_precedes_vault_and_network_access_and_can_reenable(self):
        with contextlib.redirect_stdout(io.StringIO()):
            r.main(self.args('configure', '--disable'))
        with patch.object(r, 'resolve_vault') as vault, patch.object(r, 'evaluate') as api, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(r.main(self.args('retrieve', '--profile', 'godot', '--task', 'physics')), 3)
            vault.assert_not_called()
            api.assert_not_called()
        with contextlib.redirect_stdout(io.StringIO()):
            r.main(self.args('configure', '--enable'))
        self.assertTrue(r.enabled(r.configuration(self.config), {}))
        self.assertFalse(r.enabled({'enabled': True}, {'VAULT_RETRIEVAL_ENABLED': '0'}))
        self.assertTrue(r.enabled({'enabled': False}, {'VAULT_RETRIEVAL_ENABLED': '1'}))

    def test_configured_path_available_while_disabled(self):
        r.atomic_json(self.config, {'version': 1, 'enabled': False, 'profiles': {'godot': {'vault': str(self.vault)}}})
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(r, 'evaluate') as api:
            r.main(self.args('path', '--profile', 'godot'))
        self.assertEqual(output.getvalue().strip(), str(self.vault))
        api.assert_not_called()

    def test_cli_offline_and_disabled_exit_codes(self):
        env = {**os.environ, 'VAULT_RETRIEVAL_ENABLED': '1'}
        args = self.args('retrieve', '--profile', 'godot', '--vault', str(self.vault), '--task', 'physics collision', '--offline')
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Physics.md', result.stdout)
        self.assertEqual(json.loads(result.stderr)['api_calls'], 0)
        env['VAULT_RETRIEVAL_ENABLED'] = '0'
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, '')
        self.assertTrue(json.loads(result.stderr)['disabled'])

    def test_portable_config_and_cache_locations(self):
        home = Path('/desktop/home')
        self.assertEqual(r.local_paths(home, 'linux', {})[0], home / '.config/vault-retrieval/config.json')
        self.assertEqual(r.local_paths(home, 'darwin', {})[1], home / 'Library/Caches/vault-retrieval')
        self.assertEqual(r.local_paths(home, 'win32', {'APPDATA': '/roaming', 'LOCALAPPDATA': '/local'})[0], Path('/roaming/vault-retrieval/config.json'))
        self.assertEqual(r.local_paths(home, 'linux', {'XDG_CACHE_HOME': '/cache'})[1], Path('/cache/vault-retrieval'))

    def test_bad_required_config_and_credential_fields_rejected(self):
        r.atomic_json(self.config, {'version': 1, 'profiles': {}, 'api_key': 'fake'})
        with self.assertRaises(r.RetrievalError):
            r.configuration(self.config)
        catalogue, _, _ = self.catalogue()
        with self.assertRaises(r.RetrievalError):
            r.eligible_and_required(catalogue, 'godot', {'required': 'INDEX.md'}, None, [])

    def test_response_validation_rejects_missing_and_invalid_judgments(self):
        questions = {'p': {'type': 'noul'}}
        good = {'answers': {'p': {'type': 'noul', 'noul': .7}}, 'usage': {'input_tokens': 10, 'output_tokens': 1}}
        self.assertEqual(r.validate_response(good, questions), good)
        for answer in [None, {'type': 'noul', 'noul': True}, {'type': 'noul', 'noul': float('nan')}, {'type': 'noul', 'noul': 2}]:
            with self.subTest(answer=answer), self.assertRaises(r.RetrievalError):
                r.validate_response({**good, 'answers': {'p': answer}}, questions)

    def test_jev_failure_has_no_retry_and_does_not_echo_cli_secrets(self):
        fake = subprocess.CompletedProcess(['jev'], 1, '', 'quota exhausted; credential=fake-private-key')
        with patch.object(r.subprocess, 'run', return_value=fake) as run:
            with self.assertRaises(r.RetrievalError) as error:
                r.evaluate({'task': 'physics'}, {'q': {'type': 'noul'}}, {'jev_command': ['jev']})
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('fake-private-key', str(error.exception))
        self.assertIn('--retries', run.call_args.args[0])
        self.assertEqual(run.call_args.args[0][-3:], ['0', '--timeout', '20'])

    def test_auth_failure_explains_process_access_without_echoing_secret(self):
        for kind in ['auth', 'storage']:
            with self.subTest(kind=kind):
                failure = json.dumps({'error': {'type': kind, 'message': 'credential=fake-private-key'}})
                fake = subprocess.CompletedProcess(['jev'], 1, failure, '')
                with patch.object(r.subprocess, 'run', return_value=fake) as run, self.assertRaises(r.RetrievalError) as error:
                    r.evaluate({'task': 'physics'}, {'q': {'type': 'noul'}}, {'jev_command': ['jev']})
                self.assertIn('authorized execution context', str(error.exception))
                self.assertNotIn('fake-private-key', str(error.exception))
                self.assertEqual(run.call_count, 1)

    def test_read_continuation_and_long_line_error(self):
        self.write('Godot/Read.md', 'First line.\nSecond original line.\n' + 'x' * 150 + '\n')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            r.main(self.args('read', '--profile', 'godot', '--vault', str(self.vault), '--note', 'Godot/Read.md', '--max-chars', '100'))
        self.assertEqual(stdout.getvalue(), 'First line.\nSecond original line.\n')
        self.assertEqual(json.loads(stderr.getvalue())['next_line'], 3)
        with self.assertRaises(r.RetrievalError):
            r.main(self.args('read', '--profile', 'godot', '--vault', str(self.vault), '--note', 'Godot/Read.md', '--start-line', '3', '--max-chars', '100'))

    def test_jev_traverses_multiple_relevant_branches(self):
        self.write('Architecture/Resources.md', '# Resources\n\n## Guidance\n\nShared data.\n')
        catalogue, _, _ = self.catalogue()
        eligible, _ = r.eligible_and_required(catalogue, 'godot', {}, None, [])
        states = []
        def fake(state, questions, config):
            states.append(state)
            answers = {key: {'type': q['type'], 'noul' if q['type'] == 'noul' else 'score': .9 if q['type'] == 'noul' else 2.8} for key, q in questions.items()}
            return {'answers': answers}, {'usage': {'input_tokens': 10, 'output_tokens': 2}}
        with patch.object(r, 'evaluate', side_effect=fake):
            selected, metrics = r.select_jev(catalogue, eligible, 'resources physics', {}, 8)
        self.assertEqual(set(selected), {'Godot/Physics.md', 'Architecture/Resources.md'})
        self.assertEqual(metrics['api_calls'], 2)
        self.assertEqual(metrics['usage']['input_tokens'], 20)
        self.assertTrue(all('id' in note for state in states for note in state.get('notes', {}).values()))

    def test_changes_during_selection_retry_with_all_usage_recorded(self):
        count = 0
        def fake(catalogue, eligible, task, config, maximum):
            nonlocal count
            count += 1
            if count == 1:
                self.write('Godot/New Physics.md', '# Physics\n\n## Guidance\n\nNew collision rule.\n')
            return ['Godot/Physics.md'], {'api_calls': 1, 'requests': [{'usage': {'input_tokens': 10, 'output_tokens': 2}}], 'usage': {'input_tokens': 10, 'output_tokens': 2}}
        stderr = io.StringIO()
        with patch.object(r, 'select_jev', side_effect=fake), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            r.main(self.args('retrieve', '--profile', 'godot', '--vault', str(self.vault), '--task', 'physics'))
        result = json.loads(Path(json.loads(stderr.getvalue())['result']).read_text())
        self.assertEqual(count, 2)
        self.assertEqual(result['metrics']['usage']['input_tokens'], 20)
        self.assertEqual(len(result['metrics']['requests']), 2)
        self.assertTrue(result['refresh']['during_request']['changed'])

    def test_continuous_changes_stop_after_one_selection_retry(self):
        count = 0
        def fake(catalogue, eligible, task, config, maximum):
            nonlocal count
            count += 1
            self.write('Godot/Physics.md', '# Physics\n\n## Guidance\n\nVersion ' + str(count) + '\n')
            return ['Godot/Physics.md'], {'api_calls': 1, 'usage': {'input_tokens': 10, 'output_tokens': 2}}
        with patch.object(r, 'select_jev', side_effect=fake), self.assertRaises(r.RetrievalError):
            r.main(self.args('retrieve', '--profile', 'godot', '--vault', str(self.vault), '--task', 'physics'))
        self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
