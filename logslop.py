#!/usr/bin/env python3
# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
"""LogsLop Standalone - Log Deduplication Script

Large log files are often full of repeated or near-duplicate lines.
LogsLop strips that redundancy, so you get one representative per message type.
Particularly useful when logs are too big to send or process as-is (e.g. into LLM context windows).

Usage:
  python3 logslop.py   (reads stdin)
  your-command 2>&1 | python3 logslop.py   (pipes stderr to stdout and both through logslop)

Examples:
  journalctl --no-pager | python3 logslop.py
  python3 logslop.py < your_log.txt

To add to PATH: copy to e.g. ~/.local/bin, then export PATH="$HOME/.local/bin:$PATH" (add to ~/.bashrc to persist).

Options (argparse, all optional):
  -n 5000              max clusters to track
  -t 0.6               Jaccard similarity threshold (0-1, higher = more aggressive deduping)
  --no-normalize-digits  disable digit/hex normalization (rare)
"""

import argparse
import re
import sys


def tokenize(line: str, normalize_digits: bool) -> list[str]:
    """Tokenize with optional digit and hex normalization."""
    placeholder = '\u0001'
    if normalize_digits:
        line = re.sub(r'\d+', placeholder, line)
    word_chars = r'a-zA-Z' + (placeholder if normalize_digits else '0-9') + r'_'
    tokens = re.findall(rf'[{word_chars}]+|[^\w\s]', line)
    if normalize_digits:
        hex_pattern = re.compile(r'^[' + placeholder + r'a-fA-FxX]+$')
        tokens = [placeholder if placeholder in t and hex_pattern.match(t) else t for t in tokens]
    return [t for t in tokens if t]


def jaccard(a: list[str], b: list[str]) -> float:
    """Token-counting Jaccard similarity."""
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 1.0


def process(lines, *, max_clusters=5000, threshold=0.6, normalize_digits=True):
    """Yield lines that pass through (first occurrence of each cluster).
    Emits ``  ...N...M`` markers (1-based omitted line ranges) before the next kept line; same at EOF for trailing skips."""
    clusters = []  # [(exemplar_tokens, line_text), ...] most recent first; exemplar fixed, not updated on match
    skipped = 0
    lineno = 0
    for line in lines:
        lineno += 1
        line = line.rstrip('\n\r')
        tokens = tokenize(line, normalize_digits)
        matched = False
        for i, (ex_tokens, ex_line) in enumerate(clusters):
            if jaccard(tokens, ex_tokens) >= threshold:
                matched = True
                clusters.pop(i)
                clusters.insert(0, (ex_tokens, ex_line))  # Keep exemplar; replacing causes drift
                break
        if not matched:
            if skipped > 0:
                skip_start = lineno - skipped
                skip_end = lineno - 1
                yield f"  ...{skip_start}...{skip_end}"
            yield line
            skipped = 0
            if max_clusters and len(clusters) >= max_clusters:
                clusters.pop()
            clusters.insert(0, (tokens, line))
        else:
            skipped += 1
    if skipped > 0:
        skip_start = lineno - skipped + 1
        skip_end = lineno
        yield f"  ...{skip_start}...{skip_end}"


def main():
    p = argparse.ArgumentParser(description='Reduce log redundancy: print first occurrence of each pattern.')
    p.add_argument('-n', '--max-clusters', type=int, default=5000, metavar='N', help='Max clusters to track (default: 5000)')
    p.add_argument('-t', '--threshold', type=float, default=0.6, help='Jaccard threshold for match (default: 0.6)')
    p.add_argument('--no-normalize-digits', action='store_true', help='Disable digit normalization')
    args = p.parse_args()
    c0, c1 = ("\033[36m", "\033[0m") if sys.stdout.isatty() else ("", "")
    print(f"{c0}# LogsLop: near-duplicate input lines removed.{c1}", flush=True)
    print(f"{c0}#   ...N...M  = omitted lines N through M in the original input (1-based).{c1}", flush=True)
    for line in process(sys.stdin, max_clusters=args.max_clusters, threshold=args.threshold, normalize_digits=not args.no_normalize_digits):
        print(line, flush=True)


if __name__ == '__main__':
    main()
