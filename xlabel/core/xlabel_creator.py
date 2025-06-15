from PIL import Image
from PIL import PngImagePlugin
import json

def add_xlabel_metadata_to_png(input_image_path, output_image_path, metadata):
    """
    Loads a PNG image, adds custom metadata to a tEXt chunk, and saves it.

    Args:
        input_image_path (str): Path to the input PNG file.
        output_image_path (str): Path to save the new PNG file with metadata.
        metadata (dict): The metadata to embed. For XLabel, this will be
                         structured data for classes and bounding boxes.
    """
    try:
        # Load the image
        img = Image.open(input_image_path)

        # Ensure it's a PNG
        if img.format != "PNG":
            print(f"Error: Input image '{input_image_path}' is not a PNG. Current format: {img.format}")
            # Optionally, convert to PNG here if desired
            # img = img.convert("RGBA") # Example conversion
            # print("Converted image to PNG format.")
            # Or simply return
            return

        # Create a PngInfo object to store metadata
        # This object will be populated with existing chunks if any
        info = PngImagePlugin.PngInfo()

        # Add our custom metadata
        # We'll use a 'tEXt' chunk. The key should be specific, e.g., "XLabelData"
        # The value is the JSON string of our metadata.
        # For tEXt chunks, the keyword should be 1-79 characters, no leading/trailing/consecutive spaces.
        metadata_key = "XLabelData"
        metadata_string = json.dumps(metadata)
        info.add_text(metadata_key, metadata_string)

        # Save the image with the new metadata
        # Crucially, pass the `pnginfo` argument
        img.save(output_image_path, "PNG", pnginfo=info)
        print(f"Successfully saved '{output_image_path}' with XLabel metadata.")

    except FileNotFoundError:
        print(f"Error: Input image '{input_image_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Define sample metadata
    # Structure: list of objects, each with class_name and bbox [x, y, width, height]
    sample_metadata = {
        "version": "0.1.0",
        "annotations": [
            {"class_name": "cat", "bbox": [10, 20, 150, 100]},
            {"class_name": "dog", "bbox": [75, 90, 200, 120]},
            {"class_name": "cat", "bbox": [200, 50, 80, 70]}
        ]
    }

    # Specify input and output image paths
    input_png = "sample.png"  # Make sure you have a sample.png in the same directory
    output_png_with_metadata = "sample_with_xlabel_metadata.png"

    add_xlabel_metadata_to_png(input_png, output_png_with_metadata, sample_metadata)

    # To verify (optional, we'll make a separate reader script next):
    # try:
    #     verify_img = Image.open(output_png_with_metadata)
    #     if metadata_key in verify_img.text:
    #         print(f"\nVerification: Found metadata key '{metadata_key}'")
    #         retrieved_metadata_string = verify_img.text[metadata_key]
    #         retrieved_metadata = json.loads(retrieved_metadata_string)
    #         print("Retrieved metadata:", retrieved_metadata)
    #     else:
    #         print(f"\nVerification: Metadata key '{metadata_key}' not found in output image.")
    #     verify_img.close()
    # except Exception as e:
    #     print(f"Verification error: {e}")
