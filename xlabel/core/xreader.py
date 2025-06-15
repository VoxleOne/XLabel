from PIL import Image
import json
import struct

# --- Constants ---
XLABEL_CHUNK_TYPE = b"xlDa" # The custom chunk type we are looking for

# --- Deserialization Logic ---
def deserialize_xlabel_data(chunk_data):
    """
    Deserializes the compact binary metadata from an 'xlDa' chunk
    back into a Python dictionary.
    """
    metadata_dict = {}
    offset = 0

    try:
        # --- Header (16 bytes) ---
        major_ver, minor_ver, \
        img_width, img_height, \
        num_class_names, num_annotations, \
        _reserved = struct.unpack_from("<BBHH I I", chunk_data, offset) # Corrected reserved to I (4 bytes)
        offset += 16 # Size of header

        metadata_dict["xlabel_version"] = f"{major_ver}.{minor_ver}"
        metadata_dict["image_properties"] = {
            "width": img_width,
            "height": img_height
            # filename is not stored in binary, can be added by reader if needed
        }
        
        # --- Class Names Table ---
        class_names = []
        for _ in range(num_class_names):
            name_len = struct.unpack_from("<B", chunk_data, offset)[0]
            offset += 1
            name_str = chunk_data[offset : offset + name_len].decode('utf-8')
            offset += name_len
            class_names.append(name_str)
        metadata_dict["class_names"] = class_names

        # --- Annotations Table ---
        annotations = []
        for _ in range(num_annotations):
            ann = {}
            
            class_id, \
            bbox_xmin, bbox_ymin, bbox_width, bbox_height = \
                struct.unpack_from("<H HHHH", chunk_data, offset) # class_id + 4 bbox vals
            offset += (2 + 4*2) # 2 for class_id, 8 for bbox

            ann["class_id"] = class_id
            ann["bbox"] = [bbox_xmin, bbox_ymin, bbox_width, bbox_height]

            flags = struct.unpack_from("<B", chunk_data, offset)[0]
            offset += 1

            if flags & 0x01: # has_score
                ann["score"] = struct.unpack_from("<f", chunk_data, offset)[0]
                offset += 4
            
            if flags & 0x02: # has_custom_attr
                custom_attr_len = struct.unpack_from("<H", chunk_data, offset)[0]
                offset += 2
                custom_attr_str = chunk_data[offset : offset + custom_attr_len].decode('utf-8')
                offset += custom_attr_len
                try:
                    ann["custom_attributes"] = json.loads(custom_attr_str)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not decode custom_attributes JSON: {e}. Storing as raw string.")
                    ann["custom_attributes_raw"] = custom_attr_str
            
            annotations.append(ann)
        metadata_dict["annotations"] = annotations

        return metadata_dict

    except struct.error as e:
        print(f"Error unpacking binary data: {e}. Offset: {offset}, Chunk size: {len(chunk_data)}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during deserialization: {e}")
        import traceback
        traceback.print_exc()
        return None


# --- Main PNG Handling Logic ---
def read_xlabel_metadata_from_png(image_path):
    """
    Loads a PNG image and attempts to read and deserialize custom binary
    metadata from an 'xlDa' chunk.
    """
    try:
        img = Image.open(image_path)
        
        # Pillow stores raw chunks in img.pnginfo.chunks if available
        # Each chunk is a tuple: (chunk_type_bytes, chunk_data_bytes)
        if hasattr(img, 'pnginfo') and img.pnginfo and img.pnginfo.chunks:
            for chunk_type, chunk_data in img.pnginfo.chunks:
                if chunk_type == XLABEL_CHUNK_TYPE:
                    print(f"Found '{XLABEL_CHUNK_TYPE.decode()}' chunk, size: {len(chunk_data)} bytes.")
                    return deserialize_xlabel_data(chunk_data)
            
            print(f"Metadata chunk '{XLABEL_CHUNK_TYPE.decode()}' not found in '{image_path}'.")
            return None
        else:
            print(f"No PNG chunk information available in '{image_path}'.")
            return None

    except FileNotFoundError:
        print(f"Error: Image '{image_path}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the image or its chunks: {e}")
        return None

if __name__ == "__main__":
    image_with_binary_metadata_path = "sample_with_xlabel_binary.png" # File created by xcreator.py

    print(f"Attempting to read XLabel binary metadata from: '{image_with_binary_metadata_path}'")
    retrieved_data = read_xlabel_metadata_from_png(image_with_binary_metadata_path)

    if retrieved_data:
        print("\nSuccessfully retrieved and deserialized XLabel metadata:")
        # Pretty print the reconstructed dictionary
        print(json.dumps(retrieved_data, indent=4))
    else:
        print("\nNo XLabel metadata was retrieved or an error occurred during parsing.")
