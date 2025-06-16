import json
import struct
import io
import os # For __main__ test
import logging # Import logging module

# --- Setup Logger ---
# Get a logger instance for this module
# The logger name will be 'xreader' if this file is xreader.py
logger = logging.getLogger(__name__)

# --- Custom Exceptions ---
class XLabelError(Exception):
    """Base class for exceptions related to XLabel processing."""
    pass

class XLabelFormatError(XLabelError):
    """Exception raised for errors in the XLabel data format or structure."""
    pass

class XLabelVersionError(XLabelError):
    """Exception raised for unsupported XLabel versions."""
    pass

# --- Constants ---
CHUNK_TYPE = b"xlDa"
XLABEL_SUPPORTED_VERSIONS = ["0.1.0", "0.2.0"] # Versions this reader can parse

SEG_TYPE_NONE = 0x00
SEG_TYPE_POLYGON = 0x01
SEG_TYPE_RLE = 0x02

def _parse_xlDa_chunk_data(chunk_data_bytes):
    """
    Deserializes the bytes from the xlDa chunk into a metadata dictionary.
    Raises XLabelFormatError or XLabelVersionError on parsing issues.
    """
    try:
        data_stream = io.BytesIO(chunk_data_bytes)
        metadata = {}

        # Version
        version_bytes = data_stream.read(16)
        if len(version_bytes) < 16:
            raise XLabelFormatError("Chunk data too short to read version.")
        format_version = version_bytes.split(b'\0', 1)[0].decode('utf-8')
        metadata["xlabel_version"] = format_version
        if format_version not in XLABEL_SUPPORTED_VERSIONS:
            # Log a warning but attempt to parse if it's a newer version potentially
            logger.warning(f"Unsupported XLabel version: {format_version}. Attempting to parse. Supported: {XLABEL_SUPPORTED_VERSIONS}")
            # For stricter handling, one might raise XLabelVersionError here.

        # Image Properties
        img_props = {}
        filename_bytes = data_stream.read(256)
        if len(filename_bytes) < 256: raise XLabelFormatError("Chunk data too short for filename.")
        img_props["filename"] = filename_bytes.split(b'\0', 1)[0].decode('utf-8')
        
        img_dims_bytes = data_stream.read(struct.calcsize("<II"))
        if len(img_dims_bytes) < struct.calcsize("<II"): raise XLabelFormatError("Chunk data too short for image dimensions.")
        img_props["width"], img_props["height"] = struct.unpack("<II", img_dims_bytes)
        metadata["image_properties"] = img_props

        # Class Names
        num_cn_bytes = data_stream.read(struct.calcsize("<H"))
        if len(num_cn_bytes) < struct.calcsize("<H"): raise XLabelFormatError("Chunk data too short for num_class_names.")
        num_class_names, = struct.unpack("<H", num_cn_bytes)
        class_names = []
        for _ in range(num_class_names):
            len_name_bytes = data_stream.read(struct.calcsize("<B"))
            if not len_name_bytes: raise XLabelFormatError(f"Unexpected EOF reading class name length for item {_ + 1}/{num_class_names}.")
            len_name, = struct.unpack("<B", len_name_bytes)
            
            name_bytes = data_stream.read(len_name)
            if len(name_bytes) < len_name: raise XLabelFormatError(f"Unexpected EOF reading class name for item {_ + 1}/{num_class_names}.")
            class_names.append(name_bytes.decode('utf-8'))
        metadata["class_names"] = class_names

        # Annotations
        num_ann_bytes = data_stream.read(struct.calcsize("<I"))
        if len(num_ann_bytes) < struct.calcsize("<I"): raise XLabelFormatError("Chunk data too short for num_annotations.")
        num_annotations, = struct.unpack("<I", num_ann_bytes)
        annotations = []
        for ann_idx in range(num_annotations):
            ann = {}
            try:
                ann["class_id"], = struct.unpack("<H", data_stream.read(struct.calcsize("<H")))
                ann["bbox"] = list(struct.unpack("<iiii", data_stream.read(struct.calcsize("<iiii"))))
                score_val, = struct.unpack("<f", data_stream.read(struct.calcsize("<f")))
                if score_val != -1.0: ann["score"] = score_val

                if format_version == "0.2.0":
                    seg_type_bytes = data_stream.read(struct.calcsize("<B"))
                    if not seg_type_bytes: raise XLabelFormatError(f"Annotation {ann_idx}: Unexpected EOF reading seg_type.")
                    seg_type, = struct.unpack("<B", seg_type_bytes)
                    
                    if seg_type == SEG_TYPE_POLYGON:
                        num_poly_parts, = struct.unpack("<I", data_stream.read(struct.calcsize("<I")))
                        polygons = []
                        for part_idx in range(num_poly_parts):
                            num_points, = struct.unpack("<I", data_stream.read(struct.calcsize("<I")))
                            poly_part = []
                            for _ in range(num_points): poly_part.extend(struct.unpack("<ii", data_stream.read(struct.calcsize("<ii"))))
                            polygons.append(poly_part)
                        ann["segmentation"] = polygons
                    elif seg_type == SEG_TYPE_RLE:
                        rle_h, rle_w = struct.unpack("<II", data_stream.read(struct.calcsize("<II")))
                        num_rle_counts, = struct.unpack("<I", data_stream.read(struct.calcsize("<I")))
                        rle_counts = [struct.unpack("<I", data_stream.read(struct.calcsize("<I")))[0] for _ in range(num_rle_counts)]
                        ann["segmentation"] = {"rle_size": [rle_h, rle_w], "rle_counts": rle_counts}
                    elif seg_type != SEG_TYPE_NONE:
                        logger.warning(f"Annotation {ann_idx}: Unknown segmentation type {seg_type} found.")
                
                custom_attrs_bytes_list = []
                while True:
                    byte = data_stream.read(1)
                    if not byte: raise XLabelFormatError(f"Annotation {ann_idx}: Unexpected EOF reading custom attributes (missing null terminator?).")
                    if byte == b'\0': break
                    custom_attrs_bytes_list.append(byte)
                
                if custom_attrs_bytes_list:
                    custom_attrs_json = b''.join(custom_attrs_bytes_list).decode('utf-8')
                    try:
                        ann["custom_attributes"] = json.loads(custom_attrs_json)
                    except json.JSONDecodeError as e_json:
                        logger.warning(f"Annotation {ann_idx}: JSON decode error for custom attributes: '{custom_attrs_json}'. Error: {e_json}")
                        ann["custom_attributes"] = {} # Default to empty
                else:
                    ann["custom_attributes"] = {}
                annotations.append(ann)
            except struct.error as e_struct:
                raise XLabelFormatError(f"Annotation {ann_idx}: Struct unpacking error: {e_struct}. Malformed data or insufficient bytes.")
            except EOFError: # io.BytesIO might not raise EOFError for read, but good to be aware
                 raise XLabelFormatError(f"Annotation {ann_idx}: Unexpected end of data stream while parsing.")


        metadata["annotations"] = annotations
        
        remaining_data = data_stream.read()
        if remaining_data:
            logger.warning(f"{len(remaining_data)} unread bytes in xlDa chunk. Format may have changed or parsing error.")
        return metadata

    except struct.error as e: # Catch errors from initial struct.unpack calls if any
        logger.error(f"Struct unpacking error during xlDa chunk parsing: {e}. Malformed chunk or version mismatch.")
        raise XLabelFormatError(f"Struct unpacking error: {e}") from e
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error during parsing: {e}. Check string encodings.")
        raise XLabelFormatError(f"Unicode decode error: {e}") from e
    # Let other XLabelFormatError or XLabelVersionError propagate
    except Exception as e: # Catch-all for unexpected errors
        logger.error(f"General unexpected error during xlDa chunk parsing: {e}", exc_info=True) # exc_info=True logs traceback
        raise XLabelError(f"Unexpected error parsing xlDa chunk: {e}") from e


def read_xlabel_metadata_from_png(image_path):
    """
    Reads XLabel metadata from an xlDa chunk in a PNG image file.
    Returns metadata dict or raises XLabelError (or its subclasses) on failure.
    """
    try:
        with open(image_path, "rb") as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                raise XLabelFormatError(f"File '{image_path}' is not a valid PNG file (signature mismatch).")
            
            while True:
                chunk_len_bytes = f.read(4)
                if not chunk_len_bytes: # EOF before IEND, or malformed
                    logger.warning(f"Unexpected EOF while reading chunk length in '{image_path}'.")
                    break 
                
                chunk_len = struct.unpack(">I", chunk_len_bytes)[0]
                chunk_type_bytes = f.read(4)

                if not chunk_type_bytes: # EOF
                    logger.warning(f"Unexpected EOF while reading chunk type in '{image_path}'.")
                    break

                if chunk_type_bytes == CHUNK_TYPE:
                    logger.info(f"Found '{CHUNK_TYPE.decode()}' chunk with length {chunk_len} in '{image_path}'.")
                    chunk_data = f.read(chunk_len)
                    if len(chunk_data) < chunk_len:
                         raise XLabelFormatError(f"Incomplete chunk data for '{CHUNK_TYPE.decode()}' in '{image_path}'. Expected {chunk_len}, got {len(chunk_data)}.")
                    _ = f.read(4) # Skip CRC
                    return _parse_xlDa_chunk_data(chunk_data) # Can raise XLabelFormatError
                else:
                    bytes_to_skip = chunk_len + 4 # data + CRC
                    f.seek(bytes_to_skip, 1) 
                    if chunk_type_bytes == b'IEND':
                        logger.info(f"Reached IEND chunk in '{image_path}'. '{CHUNK_TYPE.decode()}' not found prior.")
                        break 
        
        # If loop finishes without returning, chunk was not found
        logger.info(f"'{CHUNK_TYPE.decode()}' chunk not found in '{image_path}'.")
        return None # Or raise an exception like XLabelError("xlDa chunk not found")

    except FileNotFoundError:
        logger.error(f"Image file '{image_path}' not found.")
        raise # Reraise FileNotFoundError to be explicit
    except XLabelError: # Catch our custom errors and re-raise
        raise
    except Exception as e: # Catch other unexpected errors during file I/O or PNG parsing
        logger.error(f"An unexpected error occurred while reading PNG '{image_path}': {e}", exc_info=True)
        raise XLabelError(f"Unexpected error reading PNG '{image_path}': {e}") from e


if __name__ == '__main__':
    # Configure basic logging for the __main__ test
    # This will show INFO, WARNING, ERROR, CRITICAL messages to the console
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_png_path = "dummy_output_with_xlabel_v0.2.0_main.png" 
    logger.info(f"Attempting to read XLabel metadata from: {test_png_path}")

    if not os.path.exists(test_png_path):
        logger.error(f"Test file '{test_png_path}' does not exist. Please run xcreator.py test first to generate it.")
    else:
        try:
            metadata = read_xlabel_metadata_from_png(test_png_path)
            if metadata:
                logger.info("Successfully read and parsed metadata:")
                
                # For cleaner printing, remove segmentation if it ended up as None
                for ann in metadata.get("annotations", []):
                    if "segmentation" in ann and ann["segmentation"] is None:
                        del ann["segmentation"] 
                
                # Use json.dumps for pretty printing the dict
                print(json.dumps(metadata, indent=2)) # Using print here for structured output of the dict
                
                logger.info(f"Metadata Version from file: {metadata.get('xlabel_version')}")
                if metadata.get("annotations"):
                    logger.info(f"First annotation bbox: {metadata['annotations'][0].get('bbox')}")
                    if "segmentation" in metadata['annotations'][0]:
                         logger.info(f"First annotation segmentation: {metadata['annotations'][0]['segmentation']}")
            else:
                # This case should ideally be covered by an exception if read_xlabel_metadata_from_png
                # is changed to always raise on failure to find/parse.
                # If it can return None for "chunk not found", this is appropriate.
                logger.warning("xlDa chunk not found or metadata was empty (but no parsing error raised).")

        except XLabelFormatError as fmterr:
            logger.error(f"XLabel Format Error: {fmterr}")
        except XLabelVersionError as verr:
            logger.error(f"XLabel Version Error: {verr}")
        except XLabelError as xle: # Catch base XLabelError or other specific ones
            logger.error(f"XLabel Processing Error: {xle}")
        except FileNotFoundError:
            logger.error(f"Critical: Test file '{test_png_path}' disappeared before reading.") # Should be caught by os.path.exists
        except Exception as e:
            logger.error(f"An unexpected error occurred in the test: {e}", exc_info=True)
