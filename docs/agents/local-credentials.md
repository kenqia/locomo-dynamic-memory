# Locate and use an existing local DeepSeek credential

When `DEEPSEEK_API_KEY` is absent from the current process, check the existing local source before
asking the user to configure it again. This guide and its launcher contain no credential values.

## Locate the source without loading a key

From the repository root, run:

```sh
python3 scripts/with_deepseek_env.py --check
```

The check reports only whether the environment variable or the conventional local file exists,
plus the file path. It does not read the file contents, validate the key, call a provider, or use
the live-call budget. Exit status is 0 when either source is present, and 2 when both are absent.

For machine-specific setup, read `~/.config/locomo-dynamic-memory/README.md` if present. That local
document records the configured source and file permissions; keep personal setup details outside
the repository. The launcher's default file is `~/.config/locomo-dynamic-memory/deepseek.env`.

If neither source is available, report the missing source and ask for its location or local setup.
Do not ask for the key in chat, print the file, or search authentication stores and private logs.

## Confirm authority for the command

Before a live call, check the current task's authorization and remaining provider-call budget.
A configured key, this guide, and the launcher do not authorize paid calls, a full experiment,
or recovery of an old Build. Reuse authority already given for the same task; ask only for a
missing budget or a change in scope. Preserve previous calls and reservations when counting usage.

## Load the credential for one explicit command

Prefix the intended command with the launcher:

```sh
python3 scripts/with_deepseek_env.py -- <command> [arguments...]
```

Replace `<command> [arguments...]` with the authorized process. This presence-only example is
safe to run without a paid-call authorization:

```sh
python3 scripts/with_deepseek_env.py -- python3 -c \
  'import os; print("credential_present=" + str("DEEPSEEK_API_KEY" in os.environ))'
```

The launcher prefers an existing nonempty process variable. Otherwise, it parses exactly one
`DEEPSEEK_API_KEY` assignment from the local file, with optional `export`, quotes, and a comment.
It treats the file as data, executes no shell expressions, and starts the command directly with
the credential in its environment. Invalid or missing input stops before starting the command
and reports only a fixed error code. The child process's exit status becomes the launcher's status.

Choose a command that keeps credentials out of its output. The launcher does not suppress the
child's output; do not use environment-dumping commands. It does not alter the parent shell,
the credential file, shell startup files, or Codex configuration. The application still reads
credentials from its process environment and does not load `.env` itself.

## Validate or roll back

The launcher tests use synthetic credential files and make no network requests:

```sh
python3 -m pytest tests/test_credential_launcher.py -q
```

Use the project's existing development environment for pytest. Revert the navigation commit to
remove the shared guide, pointer and launcher. If removing a newly created local README, remove
only that exact file; preserve `deepseek.env`. Restore any pre-existing local README from its
backup instead of deleting it. Existing credentials and application settings require no rollback.
