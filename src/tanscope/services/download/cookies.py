import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def writable_cookies(source: Path | None) -> Iterator[Path | None]:
    if source is None or not source.exists():
        yield None
        return
    descriptor, temp_name = tempfile.mkstemp(suffix=".txt", prefix="cookies-")
    temp_path = Path(temp_name)
    try:
        with open(descriptor, "wb") as target, source.open("rb") as origin:
            shutil.copyfileobj(origin, target)
        yield temp_path
    finally:
        temp_path.unlink(missing_ok=True)
