from PIL import Image
import json

def read_xlabel_metadata_from_png(image_path):
    """
    Loads a PNG image and attempts to read custom metadata from a tEXt chunk.

    Args:
        image_path (str): Path to the PNG file.

    Returns:
        dict: The deserialized metadata if found, otherwise None.
    """
    try:
        # Load the image
        img = Image.open(image_path)

        # PNG metadata is often stored in the .info attribute or .text for tEXt chunks
        # Pillow populates img.text for tEXt, iTXt, and zTXt chunks
        metadata_key = "XLabelData" # The same key we used for writing

        if img.text and metadata_key in img.text:
            metadata_string = img.text[metadata_key]
            try:
                metadata = json.loads(metadata_string)
                return metadata
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON metadata: {e}")
                return None
        else:
            print(f"Metadata key '{metadata_key}' not found in '{image_path}'.")
            return None

    except FileNotFoundError:
        print(f"Error: Image '{image_path}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the image: {e}")
        return None

if __name__ == "__main__":
    # Specify the path to the image with embedded metadata
    image_with_metadata_path = "sample_with_xlabel_metadata.png"

    print(f"Attempting to read XLabel metadata from: '{image_with_metadata_path}'")
    retrieved_data = read_xlabel_metadata_from_png(image_with_metadata_path)

    if retrieved_data:
        print("\nSuccessfully retrieved XLabel metadata:")
        # Pretty print the JSON
        print(json.dumps(retrieved_data, indent=4))
    else:
        print("\nNo XLabel metadata was retrieved.")
