import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo

class MetadataHandler:
    """Handles reading and writing annotation data to image metadata."""
    
    METADATA_KEY = "XLabelAnnotations"

    def save_annotations(self, filepath: str, annotations: dict):
        """
        Saves annotation data to a PNG file's metadata.
        If the file is not a PNG, it will be saved as a new PNG, and the
        original file will not be modified.

        Args:
            filepath (str): Path to the image file.
            annotations (dict): A dictionary containing all annotation data.

        Returns:
            str: The path to the saved file (which may be a new .png file).
            bool: True if successful, False otherwise.
        """
        try:
            img = Image.open(filepath)
            
            # Prepare metadata
            metadata = PngInfo()
            json_data = json.dumps(annotations, indent=4)
            metadata.add_text(self.METADATA_KEY, json_data)

            # Ensure the output path has a .png extension
            if not filepath.lower().endswith('.png'):
                filepath = filepath.rsplit('.', 1)[0] + '.png'

            img.save(filepath, "PNG", pnginfo=metadata)
            return filepath, True

        except Exception as e:
            print(f"Error saving annotations to metadata: {e}")
            return filepath, False

    def load_annotations(self, filepath: str) -> dict:
        """
        Loads annotation data from an image file's metadata.

        Args:
            filepath (str): Path to the image file.

        Returns:
            dict: A dictionary containing all annotation data, or an empty dict if none found.
        """
        try:
            img = Image.open(filepath)
            
            # For PNGs, look in the standard text chunks
            if img.format == 'PNG' and self.METADATA_KEY in img.info:
                json_data = img.info[self.METADATA_KEY]
                return json.loads(json_data)

            # For JPEGs/other formats, check EXIF data (less ideal but possible)
            exif_data = img.getexif()
            if exif_data:
                # PIL uses numeric tags for EXIF data. UserComment is 37510.
                if 37510 in exif_data and exif_data[37510].startswith(self.METADATA_KEY):
                    # Extract the JSON part
                    json_data = exif_data[37510].split(':', 1)[1]
                    return json.loads(json_data)

            return {}
        except Exception as e:
            print(f"Error loading annotations from metadata: {e}")
            return {}
