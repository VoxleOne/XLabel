"""Tests for reader.py input validation guards."""

import io
import os
import struct

import pytest

from xlabel import reader


def _make_png_with_xlDa(chunk_data: bytes, tmp_dir: str) -> str:
    """Craft a minimal PNG file containing the given raw xlDa chunk bytes."""
    path = os.path.join(tmp_dir, "crafted.png")
    with open(path, "wb") as f:
        # PNG signature
        f.write(b"\x89PNG\r\n\x1a\n")
        # Minimal IHDR chunk (required for a valid PNG header; 13 bytes of data)
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        _write_chunk(f, b"IHDR", ihdr_data)
        # xlDa chunk with our crafted data
        _write_chunk(f, b"xlDa", chunk_data)
        # IEND chunk
        _write_chunk(f, b"IEND", b"")
    return path


def _write_chunk(f, chunk_type: bytes, data: bytes):
    """Write a single PNG chunk (length + type + data + CRC)."""
    import zlib

    f.write(struct.pack(">I", len(data)))
    f.write(chunk_type)
    f.write(data)
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    f.write(struct.pack(">I", crc))


def _build_valid_header(
    version: str = "0.2.0",
    filename: str = "test.png",
    width: int = 320,
    height: int = 240,
):
    """Build the standard header portion of an xlDa chunk (version + image_properties)."""
    buf = bytearray()
    buf.extend(version.encode("utf-8").ljust(16, b"\0"))
    buf.extend(filename.encode("utf-8").ljust(256, b"\0"))
    buf.extend(struct.pack("<II", width, height))
    return buf


class TestChunkSizeLimit:
    def test_oversized_chunk_rejected(self, tmp_dir):
        """A chunk whose declared length exceeds MAX_CHUNK_SIZE should be rejected."""
        path = os.path.join(tmp_dir, "huge.png")
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            # Fake an xlDa chunk with a huge declared length (no actual data)
            f.write(struct.pack(">I", reader.MAX_CHUNK_SIZE + 1))
            f.write(b"xlDa")
        with pytest.raises(reader.XLabelFormatError, match="exceeds maximum"):
            reader.read_xlabel_metadata_from_png(path)


class TestClassNameLimits:
    def test_too_many_class_names(self, tmp_dir):
        """num_class_names exceeding MAX_CLASS_NAMES is rejected."""
        buf = _build_valid_header()
        # Write num_class_names = MAX + 1 (uint16 can hold up to 65535)
        count = min(reader.MAX_CLASS_NAMES + 1, 65535)
        buf.extend(struct.pack("<H", count))
        # Don't bother writing actual names — the limit check fires first
        path = _make_png_with_xlDa(bytes(buf), tmp_dir)
        with pytest.raises(reader.XLabelFormatError, match="num_class_names"):
            reader.read_xlabel_metadata_from_png(path)


class TestAnnotationLimits:
    def test_too_many_annotations(self, tmp_dir):
        """num_annotations exceeding MAX_ANNOTATIONS is rejected."""
        buf = _build_valid_header()
        # 0 class names
        buf.extend(struct.pack("<H", 0))
        # num_annotations = huge
        buf.extend(struct.pack("<I", reader.MAX_ANNOTATIONS + 1))
        path = _make_png_with_xlDa(bytes(buf), tmp_dir)
        with pytest.raises(reader.XLabelFormatError, match="num_annotations"):
            reader.read_xlabel_metadata_from_png(path)


class TestClassIdValidation:
    def test_class_id_out_of_range(self, tmp_dir):
        """class_id >= num_class_names is rejected."""
        buf = _build_valid_header()
        # 1 class name "x"
        buf.extend(struct.pack("<H", 1))
        buf.extend(struct.pack("<B", 1))
        buf.extend(b"x")
        # 1 annotation with class_id = 5 (out of range for 1 class)
        buf.extend(struct.pack("<I", 1))
        buf.extend(struct.pack("<H", 5))  # class_id = 5
        buf.extend(struct.pack("<iiii", 0, 0, 10, 10))  # bbox
        buf.extend(struct.pack("<f", 0.9))  # score
        # segmentation type NONE
        buf.extend(struct.pack("<B", reader.SEG_TYPE_NONE))
        # empty custom_attributes
        buf.extend(b"{}\0")
        path = _make_png_with_xlDa(bytes(buf), tmp_dir)
        with pytest.raises(reader.XLabelFormatError, match="class_id"):
            reader.read_xlabel_metadata_from_png(path)


class TestCustomAttributesLimit:
    def test_missing_null_terminator_limited(self, tmp_dir):
        """Custom attributes without null terminator triggers EOF error within limit."""
        buf = _build_valid_header()
        # 1 class name
        buf.extend(struct.pack("<H", 1))
        buf.extend(struct.pack("<B", 1))
        buf.extend(b"x")
        # 1 annotation
        buf.extend(struct.pack("<I", 1))
        buf.extend(struct.pack("<H", 0))  # class_id
        buf.extend(struct.pack("<iiii", 0, 0, 10, 10))
        buf.extend(struct.pack("<f", 0.9))
        buf.extend(struct.pack("<B", reader.SEG_TYPE_NONE))
        # Custom attributes: a string without null terminator — chunk just ends
        buf.extend(b"no_null_here")
        path = _make_png_with_xlDa(bytes(buf), tmp_dir)
        with pytest.raises(reader.XLabelFormatError, match="EOF reading custom attributes"):
            reader.read_xlabel_metadata_from_png(path)


class TestUnsupportedVersion:
    def test_unsupported_version_rejected(self, tmp_dir):
        """A version not in _VERSION_PARSERS raises XLabelVersionError."""
        buf = _build_valid_header(version="0.9.0")
        # Need at least enough data for the version check
        path = _make_png_with_xlDa(bytes(buf), tmp_dir)
        with pytest.raises(reader.XLabelVersionError, match="Unsupported"):
            reader.read_xlabel_metadata_from_png(path)
