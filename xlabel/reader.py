# reader.py — MIT License
# Author: Eraldo Marques <eraldo.bernardo@gmail.com> — Created: 2025-06-16
# See LICENSE.txt for full terms. This header must be retained in redistributions.

import json
import struct
import io
import os 
import logging 

logger = logging.getLogger(__name__)

class XLabelError(Exception):
    """Base class for exceptions related to XLabel processing."""
    pass

class XLabelFormatError(XLabelError):
    """Exception raised for errors in the XLabel data format or structure."""
    pass

class XLabelVersionError(XLabelError):
    """Exception raised for unsupported XLabel versions."""
    pass

CHUNK_TYPE = b"xlDa"

SEG_TYPE_NONE = 0x00
SEG_TYPE_POLYGON = 0x01
SEG_TYPE_RLE = 0x02

# --- Input Validation Limits ---
# These caps prevent excessive memory allocation from malformed/malicious xlDa
# chunks.  They are deliberately generous — well above realistic usage — so
# that valid files are never rejected.
MAX_CLASS_NAMES = 10_000
MAX_ANNOTATIONS = 100_000
MAX_POLYGON_PARTS = 1_000
MAX_POLYGON_POINTS = 100_000
MAX_RLE_COUNTS = 10_000_000
MAX_CHUNK_SIZE = 500 * 1024 * 1024  # 500 MB
MAX_CUSTOM_ATTR_SIZE = 1 * 1024 * 1024  # 1 MB

# ---------------------------------------------------------------------------
# Version dispatch table for annotation parsing.
#
# Each version has its own annotation parser function.  To add support for a
# new XLabel format version:
#   1. Write a ``_parse_annotation_vX_Y_Z`` function following the same
#      signature as the existing ones (``data_stream``, ``ann_idx``,
#      ``num_class_names``).
#   2. Register it in ``_VERSION_PARSERS`` below.
#
# ``XLABEL_SUPPORTED_VERSIONS`` is derived from the keys of this mapping so
# the two are always in sync.
# ---------------------------------------------------------------------------

def _parse_annotation_v0_1_0(data_stream, ann_idx, num_class_names):
    """Parse a single annotation for format version 0.1.0 (no segmentation)."""
    ann = {}
    ann["class_id"], = struct.unpack("<H", data_stream.read(struct.calcsize("<H")))
    if ann["class_id"] >= num_class_names:
        raise XLabelFormatError(
            f"Ann {ann_idx}: class_id ({ann['class_id']}) >= num_class_names ({num_class_names})."
        )
    ann["bbox"] = list(struct.unpack("<iiii", data_stream.read(struct.calcsize("<iiii"))))
    score_val, = struct.unpack("<f", data_stream.read(struct.calcsize("<f")))
    if score_val != -1.0:
        ann["score"] = score_val

    # v0.1.0 has no segmentation field — skip straight to custom_attributes
    ann["custom_attributes"] = _read_custom_attributes(data_stream, ann_idx)
    return ann


def _parse_annotation_v0_2_0(data_stream, ann_idx, num_class_names):
    """Parse a single annotation for format version 0.2.0 (with segmentation)."""
    ann = {}
    ann["class_id"], = struct.unpack("<H", data_stream.read(struct.calcsize("<H")))
    if ann["class_id"] >= num_class_names:
        raise XLabelFormatError(
            f"Ann {ann_idx}: class_id ({ann['class_id']}) >= num_class_names ({num_class_names})."
        )
    ann["bbox"] = list(struct.unpack("<iiii", data_stream.read(struct.calcsize("<iiii"))))
    score_val, = struct.unpack("<f", data_stream.read(struct.calcsize("<f")))
    if score_val != -1.0:
        ann["score"] = score_val

    # --- segmentation (v0.2.0+) ---
    seg_type_bytes = data_stream.read(struct.calcsize("<B"))
    if not seg_type_bytes:
        raise XLabelFormatError(f"Ann {ann_idx}: EOF reading seg_type.")
    seg_type, = struct.unpack("<B", seg_type_bytes)

    if seg_type == SEG_TYPE_POLYGON:
        num_poly_parts_bytes = data_stream.read(struct.calcsize("<I"))
        if not num_poly_parts_bytes:
            raise XLabelFormatError(f"Ann {ann_idx} poly: EOF reading num_poly_parts.")
        num_poly_parts, = struct.unpack("<I", num_poly_parts_bytes)
        if num_poly_parts > MAX_POLYGON_PARTS:
            raise XLabelFormatError(
                f"Ann {ann_idx}: num_poly_parts ({num_poly_parts}) exceeds maximum ({MAX_POLYGON_PARTS})."
            )
        polygons = []
        for part_i in range(num_poly_parts):
            num_points_bytes = data_stream.read(struct.calcsize("<I"))
            if not num_points_bytes:
                raise XLabelFormatError(f"Ann {ann_idx} poly part {part_i + 1}: EOF reading num_points.")
            num_points, = struct.unpack("<I", num_points_bytes)
            if num_points > MAX_POLYGON_POINTS:
                raise XLabelFormatError(
                    f"Ann {ann_idx}: num_points ({num_points}) exceeds maximum ({MAX_POLYGON_POINTS})."
                )
            poly_part = []
            for pt_i in range(num_points):
                point_bytes = data_stream.read(struct.calcsize("<ii"))
                if len(point_bytes) < struct.calcsize("<ii"):
                    raise XLabelFormatError(f"Ann {ann_idx} poly point {pt_i + 1}: EOF reading coords.")
                poly_part.extend(struct.unpack("<ii", point_bytes))
            polygons.append(poly_part)
        ann["segmentation"] = polygons

    elif seg_type == SEG_TYPE_RLE:
        rle_dims_bytes = data_stream.read(struct.calcsize("<II"))
        if len(rle_dims_bytes) < struct.calcsize("<II"):
            raise XLabelFormatError(f"Ann {ann_idx} RLE: EOF reading rle_size.")
        rle_h, rle_w = struct.unpack("<II", rle_dims_bytes)

        num_rle_counts_bytes = data_stream.read(struct.calcsize("<I"))
        if not num_rle_counts_bytes:
            raise XLabelFormatError(f"Ann {ann_idx} RLE: EOF reading num_rle_counts.")
        num_rle_counts, = struct.unpack("<I", num_rle_counts_bytes)
        if num_rle_counts > MAX_RLE_COUNTS:
            raise XLabelFormatError(
                f"Ann {ann_idx}: num_rle_counts ({num_rle_counts}) exceeds maximum ({MAX_RLE_COUNTS})."
            )

        rle_counts = []
        for rc_i in range(num_rle_counts):
            count_byte = data_stream.read(struct.calcsize("<I"))
            if not count_byte:
                raise XLabelFormatError(f"Ann {ann_idx} RLE count {rc_i + 1}: EOF reading count.")
            rle_counts.append(struct.unpack("<I", count_byte)[0])
        ann["segmentation"] = {"rle_size": [rle_h, rle_w], "rle_counts": rle_counts}

    elif seg_type != SEG_TYPE_NONE:
        logger.warning(f"Ann {ann_idx}: Unknown segmentation type {seg_type}.")

    ann["custom_attributes"] = _read_custom_attributes(data_stream, ann_idx)
    return ann


def _read_custom_attributes(data_stream, ann_idx):
    """Read a null-terminated JSON string for custom attributes."""
    custom_attrs_bytes_list = []
    custom_attrs_size = 0
    while True:
        byte = data_stream.read(1)
        if not byte:
            raise XLabelFormatError(f"Ann {ann_idx}: EOF reading custom attributes.")
        if byte == b'\0':
            break
        custom_attrs_bytes_list.append(byte)
        custom_attrs_size += 1
        if custom_attrs_size > MAX_CUSTOM_ATTR_SIZE:
            raise XLabelFormatError(
                f"Ann {ann_idx}: custom_attributes exceeds maximum size ({MAX_CUSTOM_ATTR_SIZE} bytes)."
            )

    if custom_attrs_bytes_list:
        custom_attrs_json = b''.join(custom_attrs_bytes_list).decode('utf-8')
        try:
            return json.loads(custom_attrs_json)
        except json.JSONDecodeError as e_json:
            logger.warning(
                f"Ann {ann_idx}: JSON decode error for custom_attributes: "
                f"'{custom_attrs_json}'. Error: {e_json}"
            )
            return {}
    return {}


_VERSION_PARSERS = {
    "0.1.0": _parse_annotation_v0_1_0,
    "0.2.0": _parse_annotation_v0_2_0,
}

XLABEL_SUPPORTED_VERSIONS = list(_VERSION_PARSERS.keys())


def _parse_xlDa_chunk_data(chunk_data_bytes):
    """
    Deserializes the bytes from the xlDa chunk into a metadata dictionary.
    Raises XLabelFormatError or XLabelVersionError on parsing issues.
    """
    try:
        data_stream = io.BytesIO(chunk_data_bytes)
        metadata = {}

        version_bytes = data_stream.read(16)
        if len(version_bytes) < 16: raise XLabelFormatError("Chunk data too short to read version.")
        format_version = version_bytes.split(b'\0', 1)[0].decode('utf-8')
        metadata["xlabel_version"] = format_version

        parse_annotation = _VERSION_PARSERS.get(format_version)
        if parse_annotation is None:
            raise XLabelVersionError(
                f"Unsupported XLabel format version: {format_version}. "
                f"Supported versions: {XLABEL_SUPPORTED_VERSIONS}"
            )

        img_props = {}
        filename_bytes = data_stream.read(256)
        if len(filename_bytes) < 256: raise XLabelFormatError("Chunk data too short for filename.")
        img_props["filename"] = filename_bytes.split(b'\0', 1)[0].decode('utf-8')
        
        img_dims_bytes = data_stream.read(struct.calcsize("<II"))
        if len(img_dims_bytes) < struct.calcsize("<II"): raise XLabelFormatError("Chunk data too short for image dimensions.")
        img_props["width"], img_props["height"] = struct.unpack("<II", img_dims_bytes)
        metadata["image_properties"] = img_props

        num_cn_bytes = data_stream.read(struct.calcsize("<H"))
        if len(num_cn_bytes) < struct.calcsize("<H"): raise XLabelFormatError("Chunk data too short for num_class_names.")
        num_class_names, = struct.unpack("<H", num_cn_bytes)
        if num_class_names > MAX_CLASS_NAMES:
            raise XLabelFormatError(f"num_class_names ({num_class_names}) exceeds maximum ({MAX_CLASS_NAMES}).")
        class_names = []
        for i in range(num_class_names):
            len_name_bytes = data_stream.read(struct.calcsize("<B"))
            if not len_name_bytes: raise XLabelFormatError(f"EOF reading class name len {i+1}/{num_class_names}.")
            len_name, = struct.unpack("<B", len_name_bytes)
            name_bytes = data_stream.read(len_name)
            if len(name_bytes) < len_name: raise XLabelFormatError(f"EOF reading class name {i+1}/{num_class_names}.")
            class_names.append(name_bytes.decode('utf-8'))
        metadata["class_names"] = class_names

        num_ann_bytes = data_stream.read(struct.calcsize("<I"))
        if len(num_ann_bytes) < struct.calcsize("<I"): raise XLabelFormatError("Chunk data too short for num_annotations.")
        num_annotations, = struct.unpack("<I", num_ann_bytes)
        if num_annotations > MAX_ANNOTATIONS:
            raise XLabelFormatError(f"num_annotations ({num_annotations}) exceeds maximum ({MAX_ANNOTATIONS}).")
        annotations = []
        for ann_idx in range(num_annotations):
            try:
                ann = parse_annotation(data_stream, ann_idx, num_class_names)
                annotations.append(ann)
            except struct.error as e_struct:
                raise XLabelFormatError(f"Ann {ann_idx}: Struct unpack error: {e_struct}.")
        metadata["annotations"] = annotations
        
        remaining_data = data_stream.read()
        if remaining_data: logger.warning(f"{len(remaining_data)} unread bytes in xlDa chunk.")
        return metadata

    except struct.error as e: raise XLabelFormatError(f"Struct unpacking error: {e}") from e
    except UnicodeDecodeError as e: raise XLabelFormatError(f"Unicode decode error: {e}") from e
    except XLabelError: raise
    except Exception as e: logger.error(f"Unexpected error parsing xlDa chunk: {e}", exc_info=True); raise XLabelError(f"Unexpected error parsing xlDa: {e}") from e

def read_xlabel_metadata_from_png(image_path):
    """
    Reads XLabel metadata from an xlDa chunk in a PNG image file.
    Returns metadata dict or raises XLabelError (or its subclasses) on failure.
    """
    try:
        with open(image_path, "rb") as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                raise XLabelFormatError(f"File '{image_path}' not valid PNG (signature mismatch).")
            
            while True:
                chunk_len_bytes = f.read(4)
                if not chunk_len_bytes: logger.warning(f"EOF reading chunk length in '{image_path}'."); break 
                chunk_len = struct.unpack(">I", chunk_len_bytes)[0]
                chunk_type_bytes = f.read(4)
                if not chunk_type_bytes: logger.warning(f"EOF reading chunk type in '{image_path}'."); break

                if chunk_type_bytes == CHUNK_TYPE:
                    if chunk_len > MAX_CHUNK_SIZE:
                        raise XLabelFormatError(f"xlDa chunk size ({chunk_len}) exceeds maximum ({MAX_CHUNK_SIZE}).")
                    logger.info(f"Found '{CHUNK_TYPE.decode()}' chunk, length {chunk_len} in '{image_path}'.")
                    chunk_data = f.read(chunk_len)
                    if len(chunk_data) < chunk_len:
                         raise XLabelFormatError(f"Incomplete chunk data for '{CHUNK_TYPE.decode()}' in '{image_path}'. Expected {chunk_len}, got {len(chunk_data)}.")
                    _ = f.read(4) # Skip CRC
                    return _parse_xlDa_chunk_data(chunk_data)
                else:
                    f.seek(chunk_len + 4, 1) # data + CRC
                    if chunk_type_bytes == b'IEND':
                        logger.info(f"IEND reached in '{image_path}'. '{CHUNK_TYPE.decode()}' not found."); break 
        
        logger.info(f"'{CHUNK_TYPE.decode()}' chunk not found in '{image_path}'.")
        return None 

    except FileNotFoundError: logger.error(f"Image file '{image_path}' not found."); raise 
    except XLabelError: raise
    except Exception as e: logger.error(f"Unexpected error reading PNG '{image_path}': {e}", exc_info=True); raise XLabelError(f"Unexpected error reading PNG '{image_path}': {e}") from e

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_png_path = "dummy_output_with_xlabel_v0.2.0_main.png" 
    logger.info(f"Attempting to read XLabel metadata from: {test_png_path}")

    if not os.path.exists(test_png_path):
        logger.error(f"Test file '{test_png_path}' does not exist. Run xcreator.py test first.")
    else:
        try:
            metadata = read_xlabel_metadata_from_png(test_png_path)
            if metadata:
                logger.info("Successfully read and parsed metadata:")
                for ann in metadata.get("annotations", []):
                    if "segmentation" in ann and ann["segmentation"] is None: del ann["segmentation"] 
                print(json.dumps(metadata, indent=2))
                logger.info(f"Metadata Version: {metadata.get('xlabel_version')}")
                if metadata.get("annotations"):
                    logger.info(f"First annotation bbox: {metadata['annotations'][0].get('bbox')}")
                    if "segmentation" in metadata['annotations'][0]:
                         logger.info(f"First annotation segmentation: {metadata['annotations'][0]['segmentation']}")
            else:
                logger.warning("xlDa chunk not found or metadata empty (no parsing error).")
        except XLabelError as xle: logger.error(f"XLabel Processing Error: {xle}", exc_info=True)
        except Exception as e: logger.error(f"Unexpected error in test: {e}", exc_info=True)
