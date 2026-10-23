#!/usr/bin/env python3
"""Portable vault retrieval with local indexing, Jev selection, and original excerpts."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCHEMA = 1
MODEL = 'jev-1.13.0'
DEFAULT_MAX_CHARS = 28000
GENERIC_TAGS = {'godot', 'gdscript', 'codex', 'game-design', 'gameplay', 'architecture'}


class RetrievalError(Exception):
    pass


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def local_paths(home=None, platform=None, env=None):
    home, platform, env = home or Path.home(), platform or sys.platform, os.environ if env is None else env
    if platform == 'win32':
        config = Path(env.get('APPDATA', str(home / 'AppData/Roaming'))) / 'vault-retrieval'
        cache = Path(env.get('LOCALAPPDATA', str(home / 'AppData/Local'))) / 'vault-retrieval'
    elif platform == 'darwin':
        config = home / 'Library/Application Support/vault-retrieval'
        cache = home / 'Library/Caches/vault-retrieval'
    else:
        config = Path(env.get('XDG_CONFIG_HOME', str(home / '.config'))) / 'vault-retrieval'
        cache = Path(env.get('XDG_CACHE_HOME', str(home / '.cache'))) / 'vault-retrieval'
    return config / 'config.json', cache


def load_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as error:
        raise RetrievalError(f'Cannot read JSON file: {path}') from error


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix='.new-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def profiles():
    return load_json(SKILL / 'profiles.json')


def configuration(path):
    value = load_json(path, {'version': 1, 'profiles': {}})
    if not isinstance(value, dict) or value.get('version') != 1:
        raise RetrievalError('Unsupported local config version; see references/setup.md.')
    if set(value) - {'version', 'profiles', 'jev_command', 'model', 'enabled'}:
        raise RetrievalError('Local config accepts paths and model settings, never API keys.')
    if not isinstance(value.get('profiles'), dict):
        raise RetrievalError('Local config profiles must be an object.')
    if type(value.get('enabled', True)) is not bool:
        raise RetrievalError('enabled must be true or false.')
    command = value.get('jev_command')
    if command is not None and (not isinstance(command, list) or not command or
                                any(not isinstance(s, str) or not s for s in command)):
        raise RetrievalError('jev_command must be a nonempty JSON array of command arguments.')
    return value


def enabled(config, env=None):
    env = os.environ if env is None else env
    override = env.get('VAULT_RETRIEVAL_ENABLED')
    if override is None:
        return config.get('enabled', True)
    if override.lower() not in ['0', '1', 'false', 'true', 'off', 'on']:
        raise RetrievalError('VAULT_RETRIEVAL_ENABLED must be 0/1, false/true, or off/on.')
    return override.lower() in ['1', 'true', 'on']


def valid_vault(path):
    return path.is_dir() and (path / 'INDEX.md').is_file() and not (path / 'INDEX.md').is_symlink()


def resolve_vault(profile, config, explicit=None, home=None, env=None):
    home, env = home or Path.home(), os.environ if env is None else env
    spec = profiles()[profile]
    # Explicit configuration errors should not silently select a different vault.
    candidates = [explicit] if explicit else []
    if not explicit:
        candidates += [env[k] for k in spec['environment'] if env.get(k)]
        local = config.get('profiles', {}).get(profile, {})
        if not isinstance(local, dict) or set(local) - {'vault', 'required'}:
            raise RetrievalError('Profile config supports vault and required note paths only.')
        if local.get('vault'):
            candidates.append(local['vault'])
        for suffix in ['txt', 'path']:
            old = home / '.codex' / (spec['legacy_config'] + '.' + suffix)
            if old.is_file():
                candidates.append(old.read_text(encoding='utf-8-sig').strip())
    if candidates:
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            path = Path(os.path.expandvars(candidate)).expanduser()
            if valid_vault(path):
                return path.resolve()
        raise RetrievalError(f'Configured {profile} vault is invalid. Run configure --profile {profile} --vault PATH.')
    registries = [home / '.config/obsidian/obsidian.json',
                  home / 'Library/Application Support/obsidian/obsidian.json']
    if env.get('APPDATA'):
        registries.insert(0, Path(env['APPDATA']) / 'obsidian/obsidian.json')
    for registry in registries:
        try:
            entries = json.loads(registry.read_text(encoding='utf-8-sig')).get('vaults', {})
            for entry in entries.values():
                path = Path(entry.get('path', ''))
                if path.name == spec['vault_name'] and valid_vault(path):
                    return path.resolve()
        except (OSError, ValueError, AttributeError, TypeError):
            continue
    for root in [home, home / 'Documents', home / 'Obsidian', home / 'Documents/Obsidian', home / 'OneDrive/Documents']:
        path = root / spec['vault_name']
        if valid_vault(path):
            return path.resolve()
    raise RetrievalError(f'Cannot find {spec["vault_name"]}. Run configure --profile {profile} --vault PATH.')


def note_path(vault, name):
    # Treat IDs as portable vault-relative POSIX paths, never shell syntax.
    if not isinstance(name, str) or '\\' in name or not name.lower().endswith('.md'):
        raise RetrievalError('Note IDs must be relative Markdown paths with forward slashes.')
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or any(p.startswith('.') for p in path.parts):
        raise RetrievalError('Note ID is outside the visible vault.')
    candidate = vault / path
    if any((vault / Path(*path.parts[:i])).is_symlink() for i in range(1, len(path.parts) + 1)):
        raise RetrievalError('Symlinked notes are not indexed or read.')
    resolved = candidate.resolve()
    if not resolved.is_relative_to(vault.resolve()) or not resolved.is_file():
        raise RetrievalError('Note does not exist inside the vault: ' + name)
    return resolved


def frontmatter(text):
    match = re.match(r'^---\s*\n(.*?)\n---\s*(?:\n|$)', text, re.S)
    fields = {}
    if not match:
        return fields
    for key, value in re.findall(r'^([a-z_]+):\s*(.*?)\s*$', match.group(1), re.M):
        if value.startswith('[') and value.endswith(']'):
            fields[key] = [v.strip().strip('\"\'') for v in value[1:-1].split(',') if v.strip()]
        else:
            fields[key] = value.strip('\"\'')
    # Obsidian also commonly writes tags/applies_to as YAML block lists.
    for key in ['tags', 'applies_to']:
        block = re.search(r'^' + key + r':\s*\n((?:[ \t]+- .*(?:\n|$))+)', match.group(1), re.M)
        if block:
            fields[key] = [v.strip().strip('\"\'') for v in re.findall(r'^[ \t]+- (.+)$', block.group(1), re.M)]
    return fields


def sections(text):
    lines = text.splitlines(keepends=True)
    starts, in_code = [(0, '')], False
    for i, line in enumerate(lines):
        if re.match(r'^\s*(```|~~~)', line):
            in_code = not in_code
        if not in_code and re.match(r'^#{1,3} ', line):
            starts.append((i, line.lstrip('#').strip()))
    starts.append((len(lines), ''))
    return [(name, start + 1, ''.join(lines[start:end]))
            for (start, name), (end, _) in zip(starts, starts[1:]) if end > start]


def extract(name, text, sha, description):
    fields = frontmatter(text)
    parts = sections(text)
    title = next((s.strip()[2:] for s in text.splitlines() if s.startswith('# ')), Path(name).stem)
    use = next((body.split('\n', 1)[-1].strip() for heading, _, body in parts if heading.lower() == 'use this when'), '')
    search = next((body.split('\n', 1)[-1].strip() for heading, _, body in parts if heading.lower() == 'search terms'), '')
    if not description and not use:
        description = next((body.strip() for heading, _, body in parts if heading and not heading.lower().startswith('source')), '')
    tags = []
    for key in ['applies_to', 'tags']:
        value = fields.get(key, [])
        tags.extend(value if isinstance(value, list) else [value])
    return {'id': name, 'sha256': sha, 'title': title, 'status': fields.get('status', 'active'),
            'type': fields.get('type', ''), 'tags': tags,
            'description': description[:350], 'use_when': use[:500], 'search_terms': search[:350],
            'headings': [heading for heading, _, _ in parts if heading][:16],
            'required': str(fields.get('retrieval_required', '')).lower() == 'true',
            'category_override': fields.get('retrieval_category', '')}


def refresh(vault, cache):
    start = time.perf_counter()
    previous = load_json(cache / 'catalogue.json', {})
    if previous.get('schema') != SCHEMA or previous.get('vault') != str(vault):
        previous = {}
    text, raw_hash = {}, {}
    for root, directories, files in os.walk(vault, followlinks=False):
        directories[:] = sorted(d for d in directories if not d.startswith('.') and not (Path(root) / d).is_symlink())
        for filename in sorted(files):
            path = Path(root) / filename
            if path.suffix.lower() == '.md' and not filename.startswith('.') and not path.is_symlink():
                name = path.relative_to(vault).as_posix()
                raw = note_path(vault, name).read_bytes()
                text[name], raw_hash[name] = raw.decode('utf-8-sig'), digest(raw)
    if 'INDEX.md' not in text:
        raise RetrievalError('The vault must contain INDEX.md.')
    routing = digest(text['INDEX.md'].encode('utf-8'))
    links = dict(re.findall(r'^\s*- \[\[([^\]|]+)(?:\|[^\]]+)?\]\]\s*[-:]\s*(.+)$', text['INDEX.md'], re.M))
    old = previous.get('notes', {})
    updated, notes = [], {}
    for name in sorted(text):
        if name in old and old[name]['sha256'] == raw_hash[name] and previous.get('routing_hash') == routing:
            notes[name] = old[name]
        else:
            notes[name] = extract(name, text[name], raw_hash[name], links.get(name[:-3], ''))
            updated.append(name)
    deleted = sorted(set(old) - set(notes))
    metadata_path = vault / 'vault-retrieval.json'
    if metadata_path.is_symlink():
        raise RetrievalError('Vault retrieval metadata must not be a symlink.')
    metadata = load_json(metadata_path, {})
    if not isinstance(metadata, dict) or set(metadata) - {'required', 'category_descriptions'}:
        raise RetrievalError('vault-retrieval.json supports required and category_descriptions only.')
    if not isinstance(metadata.get('required', []), list) or any(not isinstance(n, str) for n in metadata.get('required', [])):
        raise RetrievalError('Vault required notes must be an array of note paths.')
    result = {'schema': SCHEMA, 'vault': str(vault), 'routing_hash': routing, 'notes': notes, 'metadata': metadata}
    result['fingerprint'] = digest(result)
    changed = result['fingerprint'] != previous.get('fingerprint')
    if changed:
        atomic_json(cache / 'catalogue.json', result)
    return result, text, {'updated': updated, 'deleted': deleted, 'changed': changed,
                          'elapsed_ms': round(1000 * (time.perf_counter() - start), 2)}


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def eligible_and_required(catalogue, profile, local, project, includes):
    spec, notes = profiles()[profile], catalogue['notes']
    if not isinstance(local.get('required', []), list) or any(not isinstance(n, str) for n in local.get('required', [])):
        raise RetrievalError('Local required notes must be an array of note paths.')
    eligible, project_roots = [], []
    for name, note in notes.items():
        if note['status'] == 'deprecated':
            continue
        folder = name.split('/')[0]
        if folder in spec['project_directories'] and name not in spec['general_project_notes']:
            if not project or not normalized(Path(name).stem).startswith(normalized(project)):
                continue
            if normalized(Path(name).stem) == normalized(project):
                project_roots.append(name)
        eligible.append(name)
    required = list(dict.fromkeys(spec['required'] + local.get('required', []) +
                                 catalogue['metadata'].get('required', []) + includes + project_roots +
                                 [n for n in eligible if notes[n]['required']]))
    for name in required:
        note_path(Path(catalogue['vault']), name)
        if name not in notes or notes[name]['status'] == 'deprecated':
            raise RetrievalError('Required note is missing or deprecated: ' + name)
    return [name for name in eligible if name not in required and notes[name]['type'] != 'index'], required


def category_tree(catalogue, eligible):
    notes = catalogue['notes']
    folders = collections.Counter(name.split('/')[0] for name in eligible)
    members = collections.defaultdict(list)
    for name in eligible:
        note = notes[name]
        folder = '/'.join(name.split('/')[:-1]) or 'General'
        category = note['category_override'] or folder
        if not note['category_override'] and folders[name.split('/')[0]] > 12:
            topic = next((t for t in note['tags'] if t not in GENERIC_TAGS), None)
            if topic:
                category += '/' + topic
        if not isinstance(category, str):
            raise RetrievalError('retrieval_category must be a string.')
        pieces = category.split('/')
        if any(not p or p in ['.', '..'] for p in pieces) or len(pieces) > 6:
            raise RetrievalError('retrieval_category must be a nonempty hierarchy of at most six levels.')
        for i in range(1, len(pieces) + 1):
            members['/'.join(pieces[:i])].append(name)
    descriptions = catalogue['metadata'].get('category_descriptions', {})
    if not isinstance(descriptions, dict) or any(not isinstance(v, str) for v in descriptions.values()):
        raise RetrievalError('category_descriptions must map category IDs to strings.')
    tree = {}
    for category, ids in sorted(members.items()):
        children = [key for key in members if key.startswith(category + '/') and key.count('/') == category.count('/') + 1]
        # Include short descriptions, not filenames alone. Rebuilt from current notes.
        examples = [{'title': notes[n]['title'], 'covers': (notes[n]['description'] or notes[n]['use_when'])[:140]}
                    for n in ids[:6]]
        tree[category] = {'description': descriptions.get(category, category.replace('/', ': ')),
                          'examples': examples, 'note_count': len(ids), 'members': ids, 'children': sorted(children)}
    return tree


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def validate_response(response, questions):
    if not isinstance(response, dict) or not isinstance(response.get('answers'), dict):
        raise RetrievalError('Jev returned an invalid answer map.')
    if set(response['answers']) != set(questions):
        raise RetrievalError('Jev response does not match the question IDs.')
    for key, question in questions.items():
        answer = response['answers'][key]
        field = 'noul' if question['type'] == 'noul' else 'score'
        limit = 1 if field == 'noul' else len(question['criteria']) - 1
        value = answer.get(field) if isinstance(answer, dict) else None
        if not isinstance(answer, dict) or answer.get('type') != question['type'] or type(value) not in [int, float] or not math.isfinite(value) or not 0 <= value <= limit:
            raise RetrievalError('Jev returned an invalid judgment.')
    usage = response.get('usage', {})
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in ['input_tokens', 'output_tokens']):
        raise RetrievalError('Jev returned invalid token usage.')
    return response


def evaluate(state, questions, config):
    request = {'state': state, 'questions': questions, 'model': config.get('model', MODEL)}
    encoded = json.dumps(request, ensure_ascii=False).encode('utf-8')
    if len(json.dumps(state, ensure_ascii=False).encode('utf-8')) > 28000 or len(encoded) > 60000:
        raise RetrievalError('Jev request exceeded the conservative context budget.')
    command = config.get('jev_command')
    if command is None and shutil.which('jev'):
        command = [shutil.which('jev')]
    start = time.perf_counter()
    if command:
        try:
            proc = subprocess.run(command + ['evaluate', '--request', '-', '--json', '--no-input', '--retries', '0', '--timeout', '20'],
                                  input=encoded.decode('utf-8'), encoding='utf-8', capture_output=True, timeout=25)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RetrievalError('Cannot run Jev. Check the local jev_command or use --offline.') from error
        if proc.returncode:
            raise RetrievalError('Jev failed. Check `jev auth status --json` and network access, or use --offline.')
        try:
            response = json.loads(proc.stdout)
        except ValueError as error:
            raise RetrievalError('Jev did not return valid JSON.') from error
    else:
        key = os.environ.get('TYPESAFE_API_KEY', '').strip()
        if not key or not key.isascii() or any(ord(c) <= 32 or ord(c) == 127 for c in key):
            raise RetrievalError('Install/configure Jev or provide TYPESAFE_API_KEY through your local secret manager. Use --offline for local search.')
        req = urllib.request.Request('https://api.typesafe.ai/v1/systemone', data=encoded,
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=20) as result:
                response = json.load(result)
        except (OSError, ValueError, urllib.error.URLError) as error:
            raise RetrievalError('TypeSafe request failed; check credentials and network access, or use --offline.') from error
    response = validate_response(response, questions)
    return response, {'wall_ms': round(1000 * (time.perf_counter() - start), 2),
                      'model': response.get('model'), 'usage': response['usage']}


def batches(items, task, kind):
    current = {}
    for key, item in items.items():
        proposal = {**current, key: item}
        if len(json.dumps({'task': task, kind: proposal}, ensure_ascii=False).encode('utf-8')) > 24000:
            if not current:
                raise RetrievalError('Task or descriptor is too large for Jev.')
            yield current
            current = {key: item}
        else:
            current = proposal
    if current:
        yield current


def select_jev(catalogue, eligible, task, config, max_notes):
    if not eligible or max_notes == 0:
        return [], {'api_calls': 0, 'requests': [], 'candidate_count': 0, 'scores': {},
                    'usage': {'input_tokens': 0, 'output_tokens': 0}}
    tree = category_tree(catalogue, eligible)
    frontier = [key for key in tree if '/' not in key]
    candidates, metrics, traversed = set(), [], []
    while frontier:
        descriptors = {key: {k: tree[key][k] for k in ['description', 'examples', 'note_count']} for key in frontier}
        accepted = []
        for batch in batches(descriptors, task, 'categories'):
            state = {'task': task, 'categories': {f'c{i}': {'id': name, **descriptor} for i, (name, descriptor) in enumerate(batch.items())}}
            questions = {f'c{i}': {'type': 'noul', 'instructions': f'Does `categories.c{i}` plausibly contain useful implementation or design guidance for `task`?',
                                   'criteria': {'true': 'Contains directly applicable guidance or a necessary constraint for the task.',
                                                'false': 'Unrelated topic or another named project; would not help this task.'}}
                         for i, name in enumerate(batch)}
            response, metric = evaluate(state, questions, config)
            metrics.append(metric)
            accepted += [name for i, name in enumerate(batch) if response['answers'][f'c{i}']['noul'] >= .30]
        if not accepted:
            accepted = frontier  # Broaden instead of making an unrecoverable early exclusion.
        frontier = []
        for name in accepted:
            traversed.append(name)
            if tree[name]['children']:
                frontier += tree[name]['children']
                child_members = set(n for child in tree[name]['children'] for n in tree[child]['members'])
                candidates.update(set(tree[name]['members']) - child_members)
            else:
                candidates.update(tree[name]['members'])
    descriptors = {name: {k: catalogue['notes'][name][k] for k in ['title', 'description', 'use_when', 'search_terms', 'headings']}
                   for name in sorted(candidates)}
    rubric = ['Unrelated; no useful guidance for this task.', 'Peripheral background only.',
              'Directly applicable guidance for a task decision or subsystem.', 'Essential concrete rules or pitfalls for this task.']
    work = []
    for batch in batches(descriptors, task, 'notes'):
        state = {'task': task, 'notes': {f'n{i}': {'id': name, **descriptor} for i, (name, descriptor) in enumerate(batch.items())}}
        questions = {f'n{i}': {'type': 'score', 'instructions': f'How useful is `notes.n{i}` as source guidance for `task`? Judge independently; multiple notes may help.', 'criteria': rubric}
                     for i, name in enumerate(batch)}
        work.append((state, questions, list(batch)))
    scores = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [(pool.submit(evaluate, state, questions, config), ids) for state, questions, ids in work]
        for future, ids in futures:
            response, metric = future.result()
            metrics.append(metric)
            scores.update({name: response['answers'][f'n{i}']['score'] for i, name in enumerate(ids)})
    selected = [name for name in sorted(scores, key=lambda n: (-scores[n], n)) if scores[name] >= 1.5][:max_notes]
    return selected, {'api_calls': len(metrics), 'requests': metrics, 'candidate_count': len(candidates),
                      'categories': traversed, 'scores': scores,
                      'usage': {key: sum(m['usage'][key] for m in metrics) for key in ['input_tokens', 'output_tokens']}}


def words(text):
    return re.findall(r'[a-z][a-z0-9_]+', text.lower())


def select_local(catalogue, eligible, task, max_notes):
    docs = {name: words(json.dumps(catalogue['notes'][name], ensure_ascii=False)) for name in eligible}
    df = collections.Counter(token for doc in docs.values() for token in set(doc))
    avg = sum(map(len, docs.values())) / max(1, len(docs))
    scores = {}
    for name, doc in docs.items():
        tf, score = collections.Counter(doc), 0.0
        for token in set(words(task)):
            freq = tf[token]
            if freq:
                score += math.log(1 + (len(docs) - df[token] + .5) / (df[token] + .5)) * freq * 2.5 / (freq + 1.5 * (.25 + .75 * len(doc) / avg))
        scores[name] = score
    selected = [n for n in sorted(scores, key=lambda n: (-scores[n], n)) if scores[n] > 0][:max_notes]
    return selected, {'api_calls': 0, 'mode': 'offline', 'scores': scores, 'usage': {'input_tokens': 0, 'output_tokens': 0}}


def excerpts(name, text, task, budget):
    """Copy original paragraphs with line references; never generate a summary."""
    query, candidates = set(words(task)), []
    for heading, start, body in sections(text):
        if heading.lower() in ['source links', 'search terms', 'links'] or start == 1:
            continue
        bonus = 4 if any(w in heading.lower() for w in ['guidance', 'rules', 'pitfalls', 'selection', 'baseline', 'principles']) else 0
        offset = 0
        for block in re.split(r'(\n\s*\n)', body):
            if block.strip():
                score = bonus + len(query & set(words(block)))
                candidates.append((score, start + offset, block))
            offset += block.count('\n')
    chosen, used = [], 0
    for _, line, block in sorted(candidates, key=lambda v: (-v[0], v[1])):
        # Long paragraphs are trimmed at whole-line boundaries, explicitly as excerpts.
        remaining = budget - used - 60
        if remaining < 120:
            break
        if len(block) > remaining:
            lines = block.splitlines(keepends=True)
            block, size = '', 0
            for part in lines:
                if size + len(part) > remaining:
                    break
                block += part
                size += len(part)
        if not block.strip():
            continue
        chosen.append((line, block))
        used += len(block) + 60
    if not chosen:
        # A note with no headings is still useful; copy a bounded original prefix.
        prefix = text[:max(0, budget - 80)]
        chosen = [(1, prefix)] if prefix else []
    return ''.join(f'\n[lines {line}-{line + block.count(chr(10))}]\n{block.rstrip()}\n' for line, block in sorted(chosen))


def output_header(full_path):
    return ('Vault guidance: full required notes, then selected original excerpts. Excerpts are not full-note reads.\n'
            'Complete originals for this selection: ' + str(full_path) + '\n')


def required_output_size(text, required, full_path):
    return len(output_header(full_path)) + sum(
        len(f'\n=== REQUIRED: {name} (full) ===\n{text[name].rstrip()}\n')
        for name in required) + 600


def render(text, required, selected, task, max_chars, full_path):
    header = output_header(full_path)
    full, output = [], [header]
    for name in required + selected:
        full.append(f'\n=== SOURCE: {name} (full) ===\n{text[name].rstrip()}\n')
    for name in required:
        output.append(f'\n=== REQUIRED: {name} (full) ===\n{text[name].rstrip()}\n')
    available = max_chars - len(''.join(output)) - 600
    if available < 0:
        raise RetrievalError('Required notes exceed the output budget. Increase --max-chars; no required content was silently dropped.')
    returned, omitted = [], []
    for i, name in enumerate(selected):
        allocation = min(1800, available // max(1, len(selected) - i))
        label = f'\n=== SELECTED: {name} (original excerpts) ===\n'
        if allocation < len(label) + 200:
            omitted.append(name)
            continue
        passage = label + excerpts(name, text[name], task, allocation - len(label))
        if len(passage) > available:
            omitted.append(name)
            continue
        output.append(passage)
        returned.append(name)
        available -= len(passage)
    footer = f'\nReturned {len(required)} required notes and {len(returned)} selected excerpts. '
    footer += f'{len(omitted)} selected notes omitted by the output budget; use the saved originals or read --note.\n'
    output.append(footer)
    result = ''.join(output)
    if len(result) > max_chars:
        raise RetrievalError('Output budget was exceeded; increase --max-chars.')
    return result, ''.join(full), returned, omitted


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    config_path, cache_path = local_paths()
    root.add_argument('--config', type=Path, default=config_path)
    root.add_argument('--cache-dir', type=Path, default=cache_path)
    sub = root.add_subparsers(dest='command', required=True)
    for command in ['configure', 'path', 'index', 'retrieve', 'read']:
        child = sub.add_parser(command)
        child.add_argument('--profile', choices=sorted(profiles()), required=command != 'configure')
        child.add_argument('--vault', help='Explicit local path, overriding discovery')
        if command == 'configure':
            child.add_argument('--jev-command-json', help='Local executable/arguments as a JSON array; never a key')
            switch = child.add_mutually_exclusive_group()
            switch.add_argument('--disable', action='store_true', help='Use the domain skills\' original vault workflow')
            switch.add_argument('--enable', action='store_true', help='Enable Jev-assisted retrieval on this desktop')
        elif command == 'retrieve':
            task = child.add_mutually_exclusive_group(required=True)
            task.add_argument('--task')
            task.add_argument('--task-file', type=Path)
            child.add_argument('--project', help='Existing project/concept note title; omit for a new game')
            child.add_argument('--include-note', action='append', default=[])
            child.add_argument('--offline', action='store_true', help='Explicit local search without any Jev call')
            child.add_argument('--max-notes', type=int, default=8)
            child.add_argument('--max-chars', type=int, help='Explicit hard output limit; by default, 28000 characters expanded to fit full required notes')
        elif command == 'read':
            child.add_argument('--note', required=True)
            child.add_argument('--start-line', type=int, default=1)
            child.add_argument('--max-chars', type=int, default=28000)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    config = configuration(args.config)
    if args.command == 'configure':
        if args.vault and not args.profile:
            raise RetrievalError('--vault requires --profile.')
        if not (args.vault or args.enable or args.disable or args.jev_command_json):
            raise RetrievalError('Provide --vault, --enable, --disable, or --jev-command-json.')
        vault = resolve_vault(args.profile, config, args.vault) if args.vault else None
        if vault:
            config['profiles'].setdefault(args.profile, {})['vault'] = str(vault)
        if args.enable or args.disable:
            config['enabled'] = args.enable
        if args.jev_command_json:
            try:
                config['jev_command'] = json.loads(args.jev_command_json)
            except ValueError as error:
                raise RetrievalError('jev_command must be a JSON array.') from error
            # Validate before saving; no broken local config is written.
            command = config['jev_command']
            if not isinstance(command, list) or not command or any(not isinstance(v, str) or not v for v in command):
                raise RetrievalError('jev_command must be a nonempty array of strings.')
        atomic_json(args.config, config)
        print(json.dumps({'config': str(args.config), 'profile': args.profile,
                          'vault': str(vault) if vault else None, 'enabled': enabled(config)}))
        return
    if args.command == 'retrieve' and not enabled(config):
        print(json.dumps({'disabled': True, 'fallback': 'Use the domain skill\'s original vault-search workflow.'}), file=sys.stderr)
        return 3
    vault = resolve_vault(args.profile, config, args.vault)
    if args.command == 'path':
        print(vault)
        return
    cache = args.cache_dir / args.profile / digest(str(vault))[:16]
    if args.command == 'read':
        if args.start_line < 1 or args.max_chars < 100:
            raise RetrievalError('read requires positive line and character limits.')
        lines = note_path(vault, args.note).read_text(encoding='utf-8-sig').splitlines(keepends=True)
        result, next_line = [], args.start_line
        for line in lines[args.start_line - 1:]:
            if len(''.join(result)) + len(line) > args.max_chars:
                break
            result.append(line)
            next_line += 1
        if not result and args.start_line <= len(lines):
            raise RetrievalError('The next original line exceeds --max-chars; increase the budget.')
        print(''.join(result), end='')
        print(json.dumps({'next_line': next_line if next_line <= len(lines) else None}), file=sys.stderr)
        return
    started = time.perf_counter()
    catalogue, text, changes = refresh(vault, cache)
    if args.command == 'index':
        available, required = eligible_and_required(catalogue, args.profile, config['profiles'].get(args.profile, {}), None, [])
        print(json.dumps({'vault': str(vault), 'notes': len(text), 'refresh': changes,
                          'required': required, 'categories': category_tree(catalogue, available)}, ensure_ascii=False))
        return
    task = args.task if args.task is not None else args.task_file.read_text(encoding='utf-8-sig')
    if not task.strip() or len(task.encode('utf-8')) > 12000 or not 0 <= args.max_notes <= 24 or (args.max_chars is not None and args.max_chars < 1000):
        raise RetrievalError('Provide a nonempty task under 12 KB, max-notes 0-24, and max-chars >= 1000.')
    all_metrics = []
    for attempt in range(2):
        eligible, required = eligible_and_required(catalogue, args.profile, config['profiles'].get(args.profile, {}), args.project, args.include_note)
        # Honor explicit limits. The default grows only for mandatory originals,
        # retaining space for bounded optional excerpts; no required text is trimmed.
        max_chars = args.max_chars if args.max_chars is not None else max(
            DEFAULT_MAX_CHARS,
            required_output_size(text, required, cache / 'requests' / ('0' * 32) / 'full-notes.md') + args.max_notes * 1800)
        # Fail before a paid lookup if mandatory originals cannot fit.
        render(text, required, [], task, max_chars, cache / 'requests/full-notes.md')
        if args.offline:
            selected, metrics = select_local(catalogue, eligible, task, args.max_notes)
        else:
            selected, metrics = select_jev(catalogue, eligible, task, config, args.max_notes)
        all_metrics.append(metrics)
        # Recheck everything after network calls: additions, renames, and edits
        # cannot silently produce a stale selection or mixed originals.
        fresh, fresh_text, fresh_changes = refresh(vault, cache)
        if fresh['fingerprint'] == catalogue['fingerprint']:
            text = fresh_text
            break
        if attempt:
            raise RetrievalError('Vault kept changing during retrieval; retry with a stable vault.')
        catalogue, text = fresh, fresh_text
        changes['during_request'] = fresh_changes
    metrics = {**metrics, 'api_calls': sum(m['api_calls'] for m in all_metrics),
               'usage': {key: sum(m['usage'][key] for m in all_metrics) for key in ['input_tokens', 'output_tokens']},
               'attempts': len(all_metrics),
               'requests': [r for m in all_metrics for r in m.get('requests', [])]}
    request_dir = cache / 'requests' / uuid.uuid4().hex
    request_dir.mkdir(parents=True, mode=0o700)
    full_path = request_dir / 'full-notes.md'
    output, full, returned, omitted = render(text, required, selected, task, max_chars, full_path)
    full_path.write_text(full, encoding='utf-8')
    result = {'profile': args.profile, 'vault': str(vault), 'catalogue_fingerprint': catalogue['fingerprint'],
              'refresh': changes, 'mode': 'offline' if args.offline else 'jev', 'required_notes': required,
              'selected_notes': selected, 'returned_excerpts': returned, 'omitted_notes': omitted,
              'output_chars': len(output), 'max_chars': max_chars,
              'elapsed_ms': round(1000 * (time.perf_counter() - started), 2),
              'metrics': metrics, 'full_originals': str(full_path)}
    atomic_json(request_dir / 'result.json', result)
    print(output, end='')
    print(json.dumps({'result': str(request_dir / 'result.json'), 'elapsed_ms': result['elapsed_ms'],
                      'output_chars': len(output), 'max_chars': max_chars,
                      'mode': result['mode'], 'api_calls': metrics['api_calls'], 'jev_usage': metrics['usage']}), file=sys.stderr)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main() or 0)
    except (RetrievalError, OSError, UnicodeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
