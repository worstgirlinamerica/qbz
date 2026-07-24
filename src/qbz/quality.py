"""Qobuz format IDs and real resolution checks."""

from __future__ import annotations


def _number(value):
    try:
        return float(str(value).lower().replace("khz", "").replace("hz", "").strip())
    except (TypeError, ValueError):
        return None


def sample_rate_khz(value):
    number = _number(value)
    if number is None:
        return None
    return number / 1000 if number >= 1000 else number


def max_resolution(*metadata):
    bit_depth = None
    sample_rate = None
    for item in metadata:
        if not isinstance(item, dict):
            continue
        bit_depth = bit_depth or _number(item.get("maximum_bit_depth") or item.get("bit_depth"))
        sample_rate = sample_rate or sample_rate_khz(
            item.get("maximum_sampling_rate") or item.get("sampling_rate")
        )
    return bit_depth, sample_rate


def target_resolution(format_id, *metadata):
    format_id = str(format_id)
    maximum_bits, maximum_rate = max_resolution(*metadata)
    if format_id == "5":
        return None, None
    if format_id == "6":
        return 16.0, 44.1
    if format_id == "7":
        return min(maximum_bits or 24.0, 24.0), min(maximum_rate or 96.0, 96.0)
    if format_id == "27":
        return maximum_bits, maximum_rate
    raise ValueError(f"Unknown Qobuz format ID: {format_id}")


def describe(format_id, *metadata):
    bits, rate = target_resolution(format_id, *metadata)
    if str(format_id) == "5":
        return "MP3 320 kbps"
    if bits is None or rate is None:
        return "availability unknown"
    return f"{int(bits) if bits.is_integer() else bits:g}-bit / {rate:g} kHz FLAC"


def validate_response(format_id, response, *metadata):
    """Raise when Qobuz returns less resolution than the selected target."""
    if str(format_id) == "5":
        return
    expected_bits, expected_rate = target_resolution(format_id, *metadata)
    actual_bits = _number(response.get("bit_depth") or response.get("bits_depth"))
    actual_rate = sample_rate_khz(response.get("sampling_rate") or response.get("sample_rate"))
    if actual_bits is None or actual_rate is None:
        raise RuntimeError("Qobuz did not return enough resolution metadata to verify the download")
    if expected_bits is not None and actual_bits < expected_bits:
        raise RuntimeError(
            f"Resolution mismatch: requested {describe(format_id, *metadata)}, "
            f"received {actual_bits:g}-bit / {actual_rate:g} kHz"
        )
    if expected_rate is not None and actual_rate < expected_rate:
        raise RuntimeError(
            f"Resolution mismatch: requested {describe(format_id, *metadata)}, "
            f"received {actual_bits:g}-bit / {actual_rate:g} kHz"
        )
