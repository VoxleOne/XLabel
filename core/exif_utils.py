import os
import json
import pyexiftool

def write_to_exif_tag(file_path, data, tag="UserComment"):
    """
    Write data to a specified EXIF tag of an image file.

    Args:
        file_path (str): Full path to the image file.
        data (str or dict): Data to store (dict is JSON-serialized).
        tag (str): EXIF tag to write to (default: UserComment).

    Returns:
        bool: True if successful, False otherwise.
    """
    if not os.path.isfile(file_path):
        print(f"Error: File {file_path} does not exist or is not a file.")
        return False

    # Convert dict to JSON string if necessary
    if isinstance(data, dict):
        try:
            data = json.dumps(data, ensure_ascii=False)
        except TypeError as e:
            print(f"Error serializing data to JSON: {e}")
            return False

    try:
        # Ensure pyexiftool is started if not already running in a context
        with pyexiftool.ExifTool() as et:
            # The tag needs to be passed as a key in a dictionary for the metadata
            # For example, if tag is "UserComment", it should be {"UserComment": data}
            # pyexiftool expects bytes for the tag value, so ensure data is encoded if it's a string
            # However, pyexiftool handles string-to-UTF8 encoding by default for common tags.
            et.execute(b"-overwrite_original", f"-{tag}={data}".encode('utf-8'), file_path.encode('utf-8'))
        return True
    except Exception as e:
        print(f"Error writing to EXIF tag {tag}: {e}")
        return False

def read_from_exif_tag(file_path, tag="UserComment", as_json=False):
    """
    Read data from a specified EXIF tag of an image file.

    Args:
        file_path (str): Full path to the image file.
        tag (str): EXIF tag to read from (default: UserComment).
        as_json (bool): If True, attempt to parse data as JSON (default: False).

    Returns:
        str or dict: Data stored in the EXIF tag, or None if not found.
    """
    if not os.path.isfile(file_path):
        print(f"Error: File {file_path} does not exist or is not a file.")
        return None

    try:
        with pyexiftool.ExifTool() as et:
            # Construct the tag argument for exiftool (e.g., "-UserComment")
            tag_arg = f"-{tag}"
            metadata_bytes = et.execute(b"-b", tag_arg.encode('utf-8'), file_path.encode('utf-8'))
            
            if not metadata_bytes:
                return None
            
            # Decode bytes to string (assuming UTF-8, common for EXIF text)
            data = metadata_bytes.decode('utf-8', errors='replace').strip()

            if data and as_json:
                try:
                    return json.loads(data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from {tag}: {e}")
                    # Return the raw data if JSON parsing fails, or handle as preferred
                    return data # Or return None, or raise error
            return data
    except Exception as e:
        print(f"Error reading from EXIF tag {tag}: {e}")
        return None