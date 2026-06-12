"""Hardware rig serial wire format.

One sample per line: NUM_SERIAL_CHANNELS comma-separated floats (cumulative
encoder degrees), CRLF-terminated, 115200 baud. No framing, no checksum —
callers drop and count malformed lines; a bad line is never fatal.
"""

from .errors import SerialDecodeError

NUM_SERIAL_CHANNELS = 8


def parse_serial_line(line: str) -> list[float]:
    """Parse one CSV sample into cumulative encoder degrees per channel.

    Raises SerialDecodeError on wrong channel count or non-numeric values.
    """
    parts = line.strip().split(",")
    if len(parts) != NUM_SERIAL_CHANNELS:
        raise SerialDecodeError(
            f"expected {NUM_SERIAL_CHANNELS} channels, got {len(parts)}: {line!r}"
        )
    try:
        return [float(part) for part in parts]
    except ValueError as exc:
        raise SerialDecodeError(f"non-numeric channel value in line: {line!r}") from exc
