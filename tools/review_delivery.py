"""Bounded, local delivery checks. This tool never executes project content."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

MIB = 1024 * 1024
MAX_META, MAX_FILE, MAX_TOTAL, MAX_FILES = MIB, 16 * MIB, 64 * MIB, 128


class InputError(Exception):
    pass


class Review(Exception):
    pass


def relative(value):
    if (not isinstance(value, str) or not value or '\x00' in value or value.startswith('/')
            or '\\' in value or ':' in value
            or any(p in ('', '.', '..') for p in value.split('/'))):
        raise InputError('Expected a strict relative path with forward slashes')
    return value


def local_project(value):
    if (not isinstance(value, str) or not value or '\x00' in value or value.startswith(('//', '\\\\', '/\\', '\\/'))
            or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', value) and not re.match(r'^[A-Za-z]:[\\/]', value)):
        raise InputError('Project must be a local filesystem directory')
    return value


def location(root, name, kind='file', missing=False):
    relative(name)
    p = root.joinpath(*name.split('/'))
    try:
        resolved = p.resolve()
        if not resolved.is_relative_to(root):
            raise InputError('Path escapes the project: ' + name)
        # Reject links in every component, including dangling links.
        current = root
        for part in name.split('/'):
            current = current / part
            if current.is_symlink():
                raise InputError('Symbolic links are unsupported: ' + name)
        if missing and not p.exists():
            if not p.parent.is_dir():
                raise InputError('Parent directory does not exist: ' + name)
            return p
        mode = p.stat().st_mode
        if not (stat.S_ISDIR(mode) if kind == 'dir' else stat.S_ISREG(mode)):
            raise InputError('Wrong filesystem object type: ' + name)
        return p
    except FileNotFoundError:
        raise Review('Missing file or directory: ' + name)


def read_bytes(root, name, limit=MAX_FILE):
    p = location(root, name)
    with p.open('rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise InputError('Expected a regular file: ' + name)
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise InputError('File exceeds byte limit: ' + name)
    return data


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def constant(value):
        raise ValueError('Nonfinite JSON number: ' + value)

    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Nonfinite JSON number')
        return result

    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=constant, parse_float=number)


def exact_keys(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        raise InputError('Unexpected object schema')


def path_list(value, nonempty=False):
    if type(value) is not list or nonempty and not value:
        raise InputError('Expected a nonempty path list' if nonempty else 'Expected a path list')
    result = [relative(item) for item in value]
    if len(set(result)) != len(result):
        raise InputError('Duplicate paths')
    return result


def load_plan(root, plan_name, receipt_name):
    try:
        plan_bytes = read_bytes(root, plan_name, MAX_META)
        plan = strict_json(plan_bytes)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError('Invalid plan JSON: ' + str(exc))
    exact_keys(plan, ('version', 'sources', 'outputs'), ('delivery_root', 'allowed_extra_files'))
    if type(plan['version']) is not int or plan['version'] != 1:
        raise InputError('Unsupported plan version')
    sources = path_list(plan['sources'], True)
    outputs = plan['outputs']
    if type(outputs) is not list or not outputs:
        raise InputError('Expected nonempty outputs')
    names = []
    for spec in outputs:
        exact_keys(spec, ('path', 'format', 'nonempty'), ('columns', 'minimum_rows'))
        names.append(relative(spec['path']))
        if spec['format'] not in ('text', 'json', 'csv', 'file') or type(spec['nonempty']) is not bool:
            raise InputError('Invalid format or nonempty flag')
        if 'columns' in spec:
            cols = spec['columns']
            if (spec['format'] != 'csv' or type(cols) is not list or not cols
                    or any(type(c) is not str or not c.strip() for c in cols)
                    or len(set(cols)) != len(cols)):
                raise InputError('Invalid CSV columns')
        if 'minimum_rows' in spec and (spec['format'] != 'csv'
                or type(spec['minimum_rows']) is not int or spec['minimum_rows'] < 0):
            raise InputError('Invalid CSV minimum_rows')
    if len(names) != len(set(names)) or set(names) & set(sources):
        raise InputError('Source and output paths must be unique and disjoint')
    extras = path_list(plan.get('allowed_extra_files', []))
    if set(extras) & set(names):
        raise InputError('Extra paths overlap outputs')
    reserved = set(sources + names)
    if plan_name == receipt_name or {plan_name, receipt_name} & reserved or receipt_name in extras:
        raise InputError('Plan or receipt path collision')
    if 'delivery_root' in plan:
        folder = relative(plan['delivery_root'])
        if folder in reserved or folder in (plan_name, receipt_name):
            raise InputError('Delivery directory collides with a file')
        if receipt_name.startswith(folder + '/'):
            raise InputError('Receipt must be outside the delivery directory')
        if any(not item.startswith(folder + '/') for item in extras):
            raise InputError('Extra paths must be within delivery_root')
        location(root, folder, 'dir')
    elif extras:
        raise InputError('allowed_extra_files requires delivery_root')
    if len(set(sources + names + extras + [plan_name])) > MAX_FILES:
        raise InputError('Too many configured files')
    return plan, sorted(sources + names + [plan_name]), hashlib.sha256(plan_bytes).hexdigest()


def snapshot(root, names, plan_name):
    hashes, total = {}, 0
    for name in names:
        data = read_bytes(root, name, MAX_META if name == plan_name else MAX_FILE)
        total += len(data)
        if total > MAX_TOTAL:
            raise InputError('Total configured bytes exceed limit')
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def formats(root, plan):
    for spec in plan['outputs']:
        name = spec['path']
        data = read_bytes(root, name)
        if spec['nonempty'] and not data:
            raise Review('Empty output: ' + name)
        try:
            if spec['format'] == 'json':
                strict_json(data)
            elif spec['format'] == 'text':
                data.decode('utf-8-sig')
            elif spec['format'] == 'csv':
                csv.field_size_limit(MAX_FILE)
                rows = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
                header = next(rows, None)
                if header is None:
                    if spec.get('columns') or spec.get('minimum_rows', 0):
                        raise ValueError('Missing CSV header')
                    continue
                if not header or any(not h.strip() for h in header) or len(set(header)) != len(header):
                    raise ValueError('Blank or duplicate CSV header')
                if 'columns' in spec and header != spec['columns']:
                    raise ValueError('CSV header order differs')
                count = 0
                for row in rows:
                    if len(row) != len(header):
                        raise ValueError('Ragged CSV row')
                    count += 1
                if count < spec.get('minimum_rows', 0):
                    raise ValueError('Too few CSV data rows')
        except (ValueError, UnicodeError, csv.Error, RecursionError) as exc:
            raise Review('Invalid output ' + name + ': ' + str(exc))


def delivery(root, plan):
    if 'delivery_root' not in plan:
        return
    folder = plan['delivery_root']
    allowed = {o['path'] for o in plan['outputs'] if o['path'].startswith(folder + '/')}
    allowed.update(plan.get('allowed_extra_files', []))
    actual, count = set(), 0
    pending = [location(root, folder, 'dir')]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > MAX_FILES:
                    raise InputError('Delivery scan entry limit exceeded')
                name = Path(entry.path).relative_to(root).as_posix()
                if entry.is_symlink():
                    location(root, name)  # Reject all links, including external targets.
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(location(root, name, 'dir'))
                else:
                    location(root, name)
                    actual.add(name)
    extra = actual - allowed
    if extra:
        raise Review('Unexpected delivery files: ' + ', '.join(sorted(extra)))


def receipt_data(root, plan_name, receipt_name, names):
    try:
        value = strict_json(read_bytes(root, receipt_name, MAX_META))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError('Invalid receipt JSON: ' + str(exc))
    exact_keys(value, ('version', 'project', 'plan', 'files'))
    if (type(value['version']) is not int or value['version'] != 1
            or type(value['project']) is not str or type(value['plan']) is not str
            or type(value['files']) is not dict):
        raise InputError('Invalid receipt field types')
    relative(value['plan'])
    for name, digest in value['files'].items():
        relative(name)
        if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
            raise InputError('Invalid receipt digest')
    if value['project'] != str(root) or value['plan'] != plan_name or set(value['files']) != set(names):
        raise Review('Receipt configuration differs from current project or plan')
    return value


def run(command, project, plan_name, receipt_name):
    # All command-line strings pass lexical checks before filesystem access.
    local_project(project)
    relative(plan_name)
    relative(receipt_name)
    root = Path(project).resolve()
    if not root.is_dir():
        raise InputError('Project directory does not exist')
    if command not in ('capture', 'check'):
        raise InputError('Unknown command')
    plan, names, plan_hash = load_plan(root, plan_name, receipt_name)
    target = location(root, receipt_name, missing=command == 'capture')
    if command == 'capture' and target.exists():
        raise InputError('Receipt already exists; choose a new versioned filename')
    recorded = receipt_data(root, plan_name, receipt_name, names) if command == 'check' else None
    before = snapshot(root, names, plan_name)
    if before[plan_name] != plan_hash:
        raise Review('Plan changed during inspection')
    formats(root, plan)
    delivery(root, plan)
    after = snapshot(root, names, plan_name)
    if before != after:
        raise Review('Configured files changed during inspection')
    if recorded and recorded['files'] != after:
        raise Review('Receipt is stale; configured bytes changed')
    if command == 'capture':
        value = dict(version=1, project=str(root), plan=plan_name, files=after)
        payload = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
        if len(payload) > MAX_META:
            raise InputError('Receipt exceeds byte limit')
        with target.open('xb') as stream:
            stream.write(payload)
    return {'state': 'ready', 'message': 'Configured files are current and valid', 'files': len(names)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('capture', 'check'))
    parser.add_argument('--project', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args(argv)
    try:
        result, code = run(args.command, args.project, args.plan, args.receipt), 0
    except Review as exc:
        result, code = {'state': 'review', 'message': str(exc)}, 1
    except (InputError, OSError, RuntimeError) as exc:
        result, code = {'state': 'error', 'message': str(exc)}, 2
    print(json.dumps(result, ensure_ascii=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
