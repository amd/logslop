# LogsLop - Log Deduplication Tool

LogsLop is a log summarization tool that removes repeated messages from log files, enabling readers and agents to home in quickly on key message events.

## Getting started

```bash
pip install logslop
```

Pipe repetitive log output through LogsLop:

```bash
journalctl --no-pager | logslop
your-command 2>&1 | logslop
logslop < your.log
```

Requires Python 3.7+. Run `logslop --help` for options (`-t` match threshold, `-n` max clusters).
