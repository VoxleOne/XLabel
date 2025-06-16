import json
import struct
# zlib is not directly used for custom chunk data by this script
import os
from PIL import Image, PngImagePlugin
import logging

# --- Setup Logger ---
logger = logging.getLogger(__name__) # Logger name will be 'xcreator'

# --- Custom Exceptions (can be shared from xreader or a common module) ---
class XLabelError(Exception):
    """Base class for exceptions related to XLabel processing."""
    pass

class XLabelFormatError(XLabelError):
    """Exception raised for errors in the XLabel data format or structure for creation."""
    pass

# --- Constants ---
XLABEL_VERSION = "0.2.0" # Version of the xlDa chunk this creator produces
CHUNK_TYPE = b"xlDa"
SEG_TYPE_NONE = 0x00
SEG_TYPE_POLYGON = 0x01
SEG_TYPE_RLE = 0x02

def _validate_metadata(metadata):
    """
    Validates the essential structure of the metadata.
    Raises XLabelFormatError if validation fails.
    """
    if not isinstance(metadata, dict): 
        raise XLabelFormatError("Metadata must be a dictionary.")
    
    # Validate image_properties
    img_props = metadata.get("image_properties")
    if not isinstance(img_props, dict): 
        raise XLabelFormatError("'image_properties' missing or not a dictionary.")
    if not all(k in img_props for k in ["filename", "width", "height"]):
        raise XLabelFormatError("'filename', 'width', or 'height' missing from 'image_properties'.")
    if not isinstance(img_props["filename"], str) or not img_props["filename"]:
        raise XLabelFormatError("'filename' in 'image_properties' must be a non-empty string.")
    if not isinstance(img_props["width"], int) or not isinstance(img_props["height"], int) or \
       img_props["width"] <= 0 or img_props["height"] <= 0:
        raise XLabelFormatError("'width' and 'height' in 'image_properties' must be positive integers.")

    # Validate class_names
    class_names = metadata.get("class_names")
    if not isinstance(class_names, list): 
        raise XLabelFormatError("'class_names' missing or not a list.")
    if not all(isinstance(name, str) for name in class_names):
        raise XLabelFormatError("All items in 'class_names' must be strings.")

    # Validate annotations
    annotations = metadata.get("annotations")
    if not isinstance(annotations, list): 
        raise XLabelFormatError("'annotations' missing or not a list.")
    
    for ann_idx, ann in enumerate(annotations):
        if not isinstance(ann, dict): 
            raise XLabelFormatError(f"Annotation at index {ann_idx} is not a dictionary.")
        if "class_id" not in ann or not isinstance(ann["class_id"], int) or \
           ann["class_id"] < 0 or ann["class_id"] >= len(class_names):
            raise XLabelFormatError(f"Annotation {ann_idx} has invalid 'class_id': {ann.get('class_id')}. Must be int and valid index for class_names.")
        if "bbox" not in ann or not isinstance(ann["bbox"], list) or len(ann["bbox"]) != 4 or \
           not all(isinstance(coord, (int, float)) for coord in ann["bbox"]): # Allow float for bbox, will be int in pack
            raise XLabelFormatError(f"Annotation {ann_idx} has invalid 'bbox': {ann.get('bbox')}. Must be list of 4 numbers.")
        # Further validation for segmentation structure if present
        segmentation = ann.get("segmentation")
        if segmentation is not None:
            if isinstance(segmentation, list): # Polygons
                for poly_idx, poly_part in enumerate(segmentation):
                    if not isinstance(poly_part, list) or len(poly_part) % 2 != 0 or len(poly_part) < 6: # Min 3 points
                         raise XLabelFormatError(f"Annotation {ann_idx}, polygon part {poly_idx} is invalid: {poly_part}. Must be list of even numbers, min 6.")
                    if not all(isinstance(p_coord, (int, float)) for p_coord in poly_part):
                         raise XLabelFormatError(f"Annotation {ann_idx}, polygon part {poly_idx} contains non-numeric coordinates.")
            elif isinstance(segmentation, dict): # RLE
                if not ("rle_counts" in segmentation and "rle_size" in segmentation):
                    raise XLabelFormatError(f"Annotation {ann_idx} RLE segmentation missing 'rle_counts' or 'rle_size'.")
                if not (isinstance(segmentation["rle_counts"], list) and 
                        all(isinstance(c, int) for c in segmentation["rle_counts"])):
                    raise XLabelFormatError(f"Annotation {ann_idx} RLE 'rle_counts' must be a list of integers.")
                if not (isinstance(segmentation["rle_size"], list) and len(segmentation["rle_size"]) == 2 and
                        all(isinstance(s, int) and s >= 0 for s in segmentation["rle_size"])):
                     raise XLabelFormatError(f"Annotation {ann_idx} RLE 'rle_size' must be a list of two non-negative integers [height, width].")
            else:
                raise XLabelFormatError(f"Annotation {ann_idx} has unknown 'segmentation' format: {type(segmentation)}.")
    return True # Validation passed

def _create_xlDa_chunk_data(metadata):
    """
    Serializes the metadata dictionary into bytes for the xlDa chunk.
    Raises XLabelFormatError or other exceptions on failure.
    Assumes metadata is already validated by _validate_metadata.
    """
    try:
        packed_data = bytearray()
        # Ensure xlabel_version in metadata is the one this creator supports
        # This should be set by add_xlabel_metadata_to_png before calling this
        version_to_write = metadata.get("xlabel_version", XLABEL_VERSION)
        if version_to_write != XLABEL_VERSION:
             logger.warning(f"Metadata 'xlabel_version' ({version_to_write}) differs from creator version ({XLABEL_VERSION}). Writing as {XLABEL_VERSION}.")
        version_bytes = XLABEL_VERSION.encode('utf-8')
        packed_data.extend(version_bytes.ljust(16, b'\0'))

        img_props = metadata["image_properties"]
        filename_bytes = img_props["filename"].encode('utf-8')
        packed_data.extend(filename_bytes.ljust(256, b'\0'))
        packed_data.extend(struct.pack("<II", img_props["width"], img_props["height"]))

        class_names = metadata["class_names"]
        packed_data.extend(struct.pack("<H", len(class_names)))
        for name in class_names:
            name_bytes = name.encode('utf-8')
            if len(name_bytes) > 255: # Max length for uint8
                raise XLabelFormatError(f"Class name '{name[:20]}...' too long (max 255 bytes after encoding).")
            packed_data.extend(struct.pack("<B", len(name_bytes)))
            packed_data.extend(name_bytes)

        annotations = metadata.get("annotations", [])
        packed_data.extend(struct.pack("<I", len(annotations)))
        for ann_idx, ann in enumerate(annotations):
            packed_data.extend(struct.pack("<H", ann["class_id"]))
            bbox = ann["bbox"] # Already validated to be list of 4 numbers
            packed_data.extend(struct.pack("<iiii", int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))) # Cast to int
            score = ann.get("score", -1.0) 
            packed_data.extend(struct.pack("<f", float(score))) # Cast to float

            segmentation = ann.get("segmentation")
            if segmentation is None:
                packed_data.extend(struct.pack("<B", SEG_TYPE_NONE))
            elif isinstance(segmentation, list): # Polygons
                packed_data.extend(struct.pack("<B", SEG_TYPE_POLYGON))
                packed_data.extend(struct.pack("<I", len(segmentation))) 
                for poly_part in segmentation: # poly_part already validated
                    num_points = len(poly_part) // 2
                    packed_data.extend(struct.pack("<I", num_points))
                    for i in range(num_points): 
                        packed_data.extend(struct.pack("<ii", int(poly_part[i*2]), int(poly_part[i*2+1]))) # Cast to int
            elif isinstance(segmentation, dict): # RLE (already validated structure)
                packed_data.extend(struct.pack("<B", SEG_TYPE_RLE))
                rle_size = segmentation["rle_size"]; rle_counts = segmentation["rle_counts"]
                packed_data.extend(struct.pack("<II", rle_size[0], rle_size[1])) 
                packed_data.extend(struct.pack("<I", len(rle_counts)))
                for count in rle_counts: packed_data.extend(struct.pack("<I", count)) # Assumes counts are int
            
            custom_attrs_json = json.dumps(ann.get("custom_attributes", {}))
            custom_attrs_bytes = custom_attrs_json.encode('utf-8')
            packed_data.extend(custom_attrs_bytes); packed_data.extend(b'\0')
        return bytes(packed_data)
    except struct.error as e:
        logger.error(f"Struct packing error during serialization (ann {ann_idx if 'ann_idx' in locals() else 'N/A'}): {e}", exc_info=True)
        raise XLabelFormatError(f"Struct packing error: {e}") from e
    except UnicodeEncodeError as e:
        logger.error(f"Unicode encoding error (e.g. in filename or classnames): {e}", exc_info=True)
        raise XLabelFormatError(f"Unicode encoding error: {e}") from e
    except Exception as e: # Catch-all for other unexpected errors
        logger.error(f"Unexpected error during metadata serialization: {e}", exc_info=True)
        raise XLabelError(f"Unexpected error during serialization: {e}") from e

def add_xlabel_metadata_to_png(input_image_path, output_image_path, metadata, overwrite=False):
    """
    Adds XLabel metadata to an image file by embedding it in a custom xlDa chunk.
    Raises XLabelError, XLabelFormatError, FileNotFoundError, or other PIL/IO errors on failure.
    Returns True on success.
    """
    if not overwrite and os.path.exists(output_image_path):
        msg = f"Output file '{output_image_path}' already exists. Use --overwrite to replace."
        logger.error(msg)
        raise FileExistsError(msg) 
        
    try:
        _validate_metadata(metadata) 
    except XLabelFormatError as e:
        logger.error(f"Metadata validation failed: {e}")
        raise 

    try:
        img = Image.open(input_image_path)
        if img.mode not in ['RGB', 'RGBA', 'L', 'LA', 'P']:
            logger.info(f"Image mode '{img.mode}' not directly saved as PNG with info. Converting to RGBA.")
            img = img.convert("RGBA")
        elif img.mode == 'P': 
             if 'transparency' in img.info: 
                 logger.info("Image mode is 'P' (Palette) with transparency. Converting to RGBA.")
                 img = img.convert("RGBA")
             else:
                 logger.info("Image mode is 'P' (Palette) without transparency. Converting to RGB.")
                 img = img.convert("RGB")

        metadata["image_properties"]["width"] = img.width
        metadata["image_properties"]["height"] = img.height
        metadata["xlabel_version"] = XLABEL_VERSION 

        chunk_data_bytes = _create_xlDa_chunk_data(metadata) 
        
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add(CHUNK_TYPE, chunk_data_bytes)
        
        img.save(output_image_path, "PNG", pnginfo=pnginfo)
        logger.info(f"Successfully embedded XLabel metadata (v{XLABEL_VERSION}) into '{output_image_path}'.")
        return True

    except FileNotFoundError:
        logger.error(f"Input image file '{input_image_path}' not found.")
        raise 
    except XLabelError: 
        raise
    except IOError as e: 
        logger.error(f"PIL/IOError processing image '{input_image_path}' or saving to '{output_image_path}': {e}", exc_info=True)
        raise XLabelError(f"Image processing/saving error: {e}") from e
    except Exception as e: 
        logger.error(f"An unexpected error occurred in add_xlabel_metadata_to_png: {e}", exc_info=True)
        raise XLabelError(f"Unexpected error adding metadata: {e}") from e

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_metadata_v0_2_0 = {
        "xlabel_version": "0.2.0", 
        "image_properties": {"filename": "test_image_creator.jpg", "width": 320, "height": 240}, 
        "class_names": ["item1", "item2_seg", "item3_rle"],
        "annotations": [
            {"class_id": 0, "bbox": [10,10,50,60], "score": 0.95, "custom_attributes": {"type":"bbox_only"}},
            {"class_id": 1, "bbox": [20,20,70,80], "score": 0.90, "segmentation": [[20,20, 90,20, 90,100, 20,100]], "custom_attributes": {"type":"poly"}},
            {"class_id": 2, "bbox": [80,80,60,70], "score": 0.88, "segmentation": {"rle_size": [240,320], "rle_counts": [100,5,200,10,5000]}, "custom_attributes": {"type":"rle"}},
        ]}
    
    invalid_metadata_test = {"image_properties": {"filename":"test.png"}}

    dummy_input_image = "dummy_input_for_xcreator_main.png"
    output_png_with_xlabel = "dummy_output_with_xlabel_v0.2.0_main.png"

    try:
        img_dummy = Image.new('RGB', (320, 240), color = 'blue') 
        img_dummy.save(dummy_input_image)
        logger.info(f"Created dummy input image: {dummy_input_image}")

        logger.info("--- Test 1: Valid Metadata ---")
        add_xlabel_metadata_to_png(dummy_input_image, output_png_with_xlabel, test_metadata_v0_2_0, overwrite=True)
        logger.info(f"Test 1 successful: Metadata v{XLABEL_VERSION} likely embedded into '{output_png_with_xlabel}'.")

        logger.info("--- Test 2: Invalid Metadata (missing fields) ---")
        try:
            add_xlabel_metadata_to_png(dummy_input_image, "invalid_output.png", invalid_metadata_test, overwrite=True)
        except XLabelFormatError as e:
            logger.info(f"Test 2 successful: Caught expected XLabelFormatError: {e}")
        except Exception as e:
            logger.error(f"Test 2 FAILED: Caught unexpected error: {e}", exc_info=True)
            
        logger.info("--- Test 3: Non-existent input image ---")
        try:
            add_xlabel_metadata_to_png("non_existent_image.png", "error_output.png", test_metadata_v0_2_0)
        except FileNotFoundError:
            logger.info(f"Test 3 successful: Caught expected FileNotFoundError.")
        except Exception as e:
            logger.error(f"Test 3 FAILED: Caught unexpected error: {e}", exc_info=True)

        logger.info("--- Test 4: Output file exists, no overwrite ---")
        if os.path.exists(output_png_with_xlabel):
            try:
                add_xlabel_metadata_to_png(dummy_input_image, output_png_with_xlabel, test_metadata_v0_2_0, overwrite=False)
            except FileExistsError:
                logger.info(f"Test 4 successful: Caught expected FileExistsError.")
            except Exception as e:
                logger.error(f"Test 4 FAILED: Caught unexpected error: {e}", exc_info=True)
        else:
            logger.warning("Skipping Test 4 as prerequisite output file does not exist.")
    except Exception as e:
        logger.error(f"Error in test setup or unhandled test case: {e}", exc_info=True)
    finally:
        if os.path.exists(dummy_input_image): os.remove(dummy_input_image)
        if os.path.exists("invalid_output.png"): os.remove("invalid_output.png")
