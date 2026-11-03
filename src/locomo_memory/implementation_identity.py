"""One implementation identity shared by run records and experiment preflight."""
import hashlib
from pathlib import Path


def implementation_sha256():
    return hashlib.sha256(b''.join(path.name.encode() + path.read_bytes() for path in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
