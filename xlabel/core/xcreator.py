from PIL import Image
from PIL import PngImagePlugin
import json
import struct

# --- Constants ---
XLABEL_CHUNK_TYPE = b"xlDa" # Custom chunk type: ancillary, private, safe to copy
CURRENT_XLABEL_VERSION = "0.1.0" # For the metadata structure itself

# --- Serialization Logic ---
def serialize_xlabel_data(metadata_dict):
    """
    Serializes the refined metadata dictionary into a compact binary format.
    """
    buffer = bytearray()

    # --- Header (16 bytes) ---
    try:
        version_parts = metadata_dict.get("xlabel_version", CURRENT_XLABEL_VERSION).split('.')
        major_ver = int(version_parts[0])
        minor_ver = int(version_parts[1])
    except Exception:
        major_ver, minor_ver = 0, 1 # Default if parsing fails

    buffer.extend(struct.pack("<B", major_ver))  # xlabel_version_major (1 byte)
    buffer.extend(struct.pack("<B", minor_ver))  # xlabel_version_minor (1 byte)

    img_props = metadata_dict.get("image_properties", {})
    buffer.extend(struct.pack("<H", img_props.get("width", 0)))    # image_width (2 bytes)
    buffer.extend(struct.pack("<H", img_props.get("height", 0)))   # image_height (2 bytes)

    class_names = metadata_dict.get("class_names", [])
    buffer.extend(struct.pack("<H", len(class_names)))             # num_class_names (2 bytes)

    annotations = metadata_dict.get("annotations", [])
    buffer.extend(struct.pack("<I", len(annotations)))             # num_annotations (4 bytes)

    buffer.extend(b'\x00\x00\x00\x00')                             # reserved (4 bytes)

    # --- Class Names Table ---
    for name_str in class_names:
        name_bytes = name_str.encode('utf-8')
        name_len = len(name_bytes)
        if name_len > 255:
            raise ValueError(f"Class name '{name_str}' is too long (max 255 bytes UTF-8).")
        buffer.extend(struct.pack("<B", name_len))                 # class_name_N_length (1 byte)
        buffer.extend(name_bytes)                                  # class_name_N_string

    # --- Annotations Table ---
    for ann in annotations:
        buffer.extend(struct.pack("<H", ann.get("class_id", 0)))   # annotation_M_class_id (2 bytes)

        bbox = ann.get("bbox", [0,0,0,0])
        if len(bbox) != 4: raise ValueError("Bounding box must have 4 elements.")
        buffer.extend(struct.pack("<HHHH", bbox[0], bbox[1], bbox[2], bbox[3])) # xmin, ymin, w, h (8 bytes)

        flags = 0
        score_data = b""
        custom_attr_data = b""

        if "score" in ann and ann["score"] is not None:
            flags |= 0x01  # Set has_score flag
            score_data = struct.pack("<f", float(ann["score"]))    # score (4 bytes)

        if "custom_attributes" in ann and ann["custom_attributes"]:
            flags |= 0x02  # Set has_custom_attr flag
            custom_attr_str = json.dumps(ann["custom_attributes"], separators=(',', ':')) # Compact JSON
            custom_attr_bytes = custom_attr_str.encode('utf-8')
            custom_attr_len = len(custom_attr_bytes)
            if custom_attr_len > 65535:
                raise ValueError("Custom attributes JSON is too long (max 65535 bytes UTF-8).")
            custom_attr_data = struct.pack("<H", custom_attr_len) + custom_attr_bytes # len + data

        buffer.extend(struct.pack("<B", flags))                    # annotation_M_flags (1 byte)
        if score_data:
            buffer.extend(score_data)
        if custom_attr_data:
            buffer.extend(custom_attr_data)

    return bytes(buffer)


# --- Main PNG Handling Logic ---
def add_xlabel_metadata_to_png(input_image_path, output_image_path, metadata_dict):
    """
    Loads a PNG image, adds custom binary metadata to an 'xlDa' chunk, and saves it.
    """
    try:
        img = Image.open(input_image_path)
        if img.format != "PNG": # Ensure it's PNG or convert
            print(f"Warning: Input image '{input_image_path}' is {img.format}. Converting to PNG.")
            img = img.convert("RGBA" if img.mode != 'RGB' else 'RGB')


        # Update image properties in metadata if not already set or to ensure accuracy
        metadata_dict.setdefault("image_properties", {})
        metadata_dict["image_properties"]["filename"] = metadata_dict["image_properties"].get("filename", input_image_path.split('/')[-1].split('\\')[-1])
        metadata_dict["image_properties"]["width"] = metadata_dict["image_properties"].get("width", img.width)
        metadata_dict["image_properties"]["height"] = metadata_dict["image_properties"].get("height", img.height)
        metadata_dict["xlabel_version"] = metadata_dict.get("xlabel_version", CURRENT_XLABEL_VERSION)


        serialized_data = serialize_xlabel_data(metadata_dict)

        # PngInfo object. Pillow handles existing chunks.
        info = PngImagePlugin.PngInfo()

        # Add our custom binary chunk.
        # Pillow's PngInfo().chunks is a list of (type, data) tuples.
        # We need to ensure our chunk is added. If other chunks exist, they'd be in img.pnginfo.chunks
        # For a fresh PngInfo, we just add.
        # If img.pnginfo exists, we might want to copy existing ancillary chunks.
        # For simplicity now, we just add our chunk.
        # A more robust solution would be to read existing chunks from img.pnginfo
        # and append ours, then pass that to save.

        # Let's try to preserve existing chunks if possible
        existing_chunks = []
        if hasattr(img, 'pnginfo') and img.pnginfo:
            existing_chunks = img.pnginfo.chunks
        
        info.chunks = existing_chunks
        
        # Remove any pre-existing 'xlDa' chunk before adding the new one
        info.chunks = [chunk for chunk in info.chunks if chunk[0] != XLABEL_CHUNK_TYPE]
        info.chunks.append((XLABEL_CHUNK_TYPE, serialized_data))


        img.save(output_image_path, "PNG", pnginfo=info)
        print(f"Successfully saved '{output_image_path}' with XLabel binary metadata (chunk '{XLABEL_CHUNK_TYPE.decode()}').")
        print(f"Size of XLabel data: {len(serialized_data)} bytes.")

    except FileNotFoundError:
        print(f"Error: Input image '{input_image_path}' not found.")
    except Exception as e:
        print(f"An error occurred in add_xlabel_metadata_to_png: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Define sample metadata using the refined structure
    refined_sample_metadata = {
        "xlabel_version": CURRENT_XLABEL_VERSION,
        "image_properties": {
            # width and height will be auto-filled if not provided or can be overridden
        },
        "class_names": ["cat", "dog", "person", "bicycle"],
        "annotations": [
            {
                "class_id": 0,  # cat
                "bbox": [10, 20, 150, 100], # x_min, y_min, width, height
                "score": 0.95,
                "custom_attributes": {"occluded": False, "pose": "sitting"}
            },
            {
                "class_id": 1,  # dog
                "bbox": [75, 90, 200, 120],
                "score": 0.88
            },
            {
                "class_id": 0,  # cat
                "bbox": [200, 50, 80, 70],
                # No score, no custom_attributes
            },
            {
                "class_id": 3, # bicycle
                "bbox": [50, 50, 100, 100],
                "custom_attributes": {"color": "red"}
            }
        ]
    }

    input_png_file = "sample.png"  # Make sure you have a sample.png
    output_png_with_binary_metadata = "sample_with_xlabel_binary.png"

    # Create a dummy sample.png if it doesn't exist for testing
    try:
        with open(input_png_file, "rb") as f:
            pass
    except FileNotFoundError:
        print(f"Creating a dummy '{input_png_file}' for testing.")
        dummy_img = Image.new("RGB", (300, 200), color="blue")
        dummy_img.save(input_png_file, "PNG")
        print(f"Dummy '{input_png_file}' created. Please replace with a real image if needed.")


    add_xlabel_metadata_to_png(input_png_file, output_png_with_binary_metadata, refined_sample_metadata)
