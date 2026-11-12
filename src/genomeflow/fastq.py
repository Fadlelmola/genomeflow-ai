"""Read standard four-line, Phred+33 FASTQ records."""
import gzip
from contextlib import ExitStack
from itertools import zip_longest
from pathlib import Path


def records(stream):
    for index, header in enumerate(stream, 1):
        sequence = stream.readline().rstrip(b"\r\n").upper()
        plus = stream.readline()
        quality = stream.readline().rstrip(b"\r\n")
        name = header[1:].split()
        if (not header.startswith(b"@") or not name or not plus.startswith(b"+")
                or not sequence or sequence.strip(b"ACGTURYSWKMBDHVN")
                or len(sequence) != len(quality) or min(quality) < 33 or max(quality) > 126):
            raise ValueError(f"Invalid FASTQ record {index}. Check the four lines and Phred+33 encoding.")
        yield name[0], sequence, quality


def analyze(paths):
    reads = bases = q30 = gc = ambiguous = 0
    if len(paths) not in (1, 2):
        raise ValueError("Select one FASTQ or two mate files.")
    if len(paths) == 2 and Path(paths[0]).samefile(paths[1]):
        raise ValueError("Choose distinct mate files.")
    with ExitStack() as stack:
        inputs = []
        for path in paths:
            raw = stack.enter_context(open(path, "rb"))
            stream = stack.enter_context(gzip.GzipFile(fileobj=raw)) if raw.peek(2)[:2] == b"\x1f\x8b" else raw
            inputs.append(records(stream))
        for group in zip_longest(*inputs):
            if len(group) == 2:
                if None in group or group[0][0].removesuffix(b"/1") != group[1][0].removesuffix(b"/2"):
                    raise ValueError("Mate files have different read identifiers, order, or lengths.")
            for _, sequence, quality in group:
                reads += 1
                bases += len(sequence)
                q30 += len(quality.translate(None, bytes(range(63))))
                gc += sequence.count(b"G") + sequence.count(b"C")
                ambiguous += sequence.count(b"N")
    if not reads:
        raise ValueError("The FASTQ contains no reads.")
    return reads, bases, q30, gc, ambiguous
