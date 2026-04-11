"""
XLabel Basic Usage Example

Demonstrates how to embed and read annotation metadata
in a PNG file using the XLabel format (v0.2.0).
"""

import json
import os
import tempfile

from PIL import Image

from xlabel import creator, reader


def main():
    # 1. Create a test image
    with tempfile.TemporaryDirectory() as tmpdir:
        input_image_path = os.path.join(tmpdir, "test_image.png")
        output_xlabel_path = os.path.join(tmpdir, "test_image_xlabel.png")

        img = Image.new("RGB", (320, 240), color="blue")
        img.save(input_image_path)
        print(f"Created test image: {input_image_path}")

        # 2. Define metadata matching the XLabel v0.2.0 schema
        metadata = {
            "image_properties": {
                "filename": "test_image.png",
                "width": 320,
                "height": 240,
            },
            "class_names": ["cat", "dog"],
            "annotations": [
                {
                    "class_id": 0,
                    "bbox": [10, 20, 100, 80],
                    "score": 0.95,
                    "custom_attributes": {"color": "orange"},
                },
                {
                    "class_id": 1,
                    "bbox": [150, 50, 120, 100],
                    "score": 0.88,
                    "segmentation": [
                        [150, 50, 270, 50, 270, 150, 150, 150]
                    ],
                    "custom_attributes": {},
                },
            ],
        }

        # 3. Embed metadata into the PNG using the creator
        creator.add_xlabel_metadata_to_png(
            input_image_path, output_xlabel_path, metadata, overwrite=True
        )
        print(f"Embedded XLabel metadata into: {output_xlabel_path}")

        # 4. Read the metadata back using the reader
        read_metadata = reader.read_xlabel_metadata_from_png(output_xlabel_path)

        # 5. Print the round-tripped metadata
        if read_metadata:
            print("\nSuccessfully read metadata back:")
            print(json.dumps(read_metadata, indent=2))
            print(f"\nXLabel version: {read_metadata.get('xlabel_version')}")
            print(f"Number of annotations: {len(read_metadata.get('annotations', []))}")
            print(f"Class names: {read_metadata.get('class_names')}")
        else:
            print("ERROR: No XLabel metadata found in the output file.")

        # 6. Demonstrate error handling
        print("\n--- Error handling examples ---")
        try:
            reader.read_xlabel_metadata_from_png("/nonexistent/path.png")
        except FileNotFoundError:
            print("Caught expected FileNotFoundError for missing file.")

        try:
            creator.add_xlabel_metadata_to_png(
                input_image_path, "bad_output.png", {"bad": "metadata"},
                overwrite=True,
            )
        except creator.XLabelFormatError as e:
            print(f"Caught expected XLabelFormatError: {e}")


if __name__ == "__main__":
    main()
