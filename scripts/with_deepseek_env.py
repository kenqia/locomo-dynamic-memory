"""Run an explicit command with the existing local DeepSeek credential, without a shell."""

import argparse
import json
import os
from pathlib import Path
import shlex
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check source presence only; do not load a key or run a command.')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if args.check and command or not args.check and not command:
        parser.error('Use --check alone, or -- followed by a command.')
    path = Path.home() / '.config/locomo-dynamic-memory/deepseek.env'
    environment = os.environ.copy()
    try:
        if args.check:
            present = bool(environment.get('DEEPSEEK_API_KEY'))
            file_present = path.is_file()
            print(json.dumps({'environment_present': present, 'credential_file_present': file_present,
                              'credential_file': str(path)}))
            return 0 if present or file_present else 2
        if not environment.get('DEEPSEEK_API_KEY'):
            values = []
            for line in path.read_text().splitlines():
                name, separator, value = line.strip().removeprefix('export ').partition('=')
                if separator and name.strip() == 'DEEPSEEK_API_KEY':
                    parts = shlex.split(value, comments=True)
                    if len(parts) != 1 or not parts[0] or '\x00' in parts[0]:
                        raise ValueError
                    values.append(parts[0])
            if len(values) != 1:
                raise ValueError
            environment['DEEPSEEK_API_KEY'] = values[0]
    except OSError:
        print('credential_source_unavailable', file=sys.stderr)
        return 2
    except ValueError:
        print('credential_file_invalid', file=sys.stderr)
        return 2
    try:
        os.execvpe(command[0], command, environment)
    except (OSError, ValueError):
        print('credential_command_start_failed', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
