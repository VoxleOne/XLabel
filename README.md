# XLabel: Self-Contained Image Annotations

**XLabel** is a Python toolkit for embedding computer vision annotations directly into PNG image files using custom data chunks. This approach simplifies dataset management by keeping images and their labels together in a single file, eliminating the need for separate "sidecar" annotation files (like JSON, XML, or TXT).

The tool provides a command-line interface (`xlabel_cli.py`) and a set of Python modules to:
*   Create XLabel PNGs by embedding structured JSON metadata.
*   Read embedded metadata from XLabel PNGs.
*   Convert between XLabel PNGs and common annotation formats (COCO, Pascal VOC, YOLO).
*   Support for both single-file and batch processing operations.

## Core Idea & Why XLabel?

Computer Vision image labels are metadata. Instead of relying on external files that can get mismatched or lost, XLabel stores this metadata directly within the PNG image itself using a custom chunk type named `xlDa` (XLabel Data). This makes datasets more portable and easier to manage.

**Key Use Cases:**

*   **Smaller, Proprietary Datasets:** For research or internal projects where managing numerous sidecar files for a modest number of images becomes cumbersome, XLabel offers a streamlined, single-file-per-image approach.
*   **Fine-Tuning Datasets:** Ideal for creating and managing small, specialized datasets for fine-tuning larger pre-trained models. For example, a dataset of "Zebu cattle" images (underrepresented in COCO) can be easily curated with XLabel to fine-tune a general "cow" detection model.
*   **Confidential Datasets:** While not a cryptographic solution, embedding data within the image can act as a mild layer of obfuscation, as the annotations are not immediately visible as separate files. This can be useful in scenarios where data privacy is a concern and casual browsing of annotation files is to be discouraged.
*   **Simplified Data Transfer & Archival:** Bundling images and labels simplifies sharing, backup, and archival of datasets.
*   **Educational Purposes:** Provides a clear example of how metadata can be embedded within file formats and encourages thinking about data structure.

The `xlDa` chunk stores:
*   A version string for the XLabel format.
*   Image properties (original filename, width, height).
*   A list of class names.
*   A list of annotations, each including:
    *   `class_id` (index into the class names list).
    *   Bounding box (`bbox`: `[xmin, ymin, width, height]`).
    *   Optional confidence `score`.
    *   Optional `segmentation` data (polygons or RLE).
    *   Optional `custom_attributes` (a flexible JSON string for additional metadata).

## Features

*   **Self-Contained Annotations:** Labels travel with the image.
*   **CLI Tool (`xlabel_cli.py`):**
    *   `create`: Embed JSON annotations into a standard PNG, creating an XLabel PNG.
        *   `single`: Process one image and one JSON file.
        *   `batch`: Process a directory of images and a directory of corresponding JSON files.
    *   `read`: Extract embedded XLabel metadata from an XLabel PNG and output as JSON.
        *   `single`: Read from one XLabel PNG.
        *   `batch`: Read from a directory of XLabel PNGs, outputting individual JSON files.
    *   `convert`: Convert annotations between XLabel PNGs and other standard formats.
        *   `2xlabel`: Convert from COCO, VOC, or YOLO to XLabel PNG(s).
            *   `--single`: Convert a single annotation file (and its associated image) to one XLabel PNG.
            *   `--batch`: Convert a dataset (e.g., one COCO JSON + image dir, or dirs of VOC XMLs/YOLO TXTs + image dir) to multiple XLabel PNGs.
        *   `fromxlabel`: Convert from XLabel PNG(s) to COCO, VOC, or YOLO.
            *   `--single`: Convert one XLabel PNG to the target format.
            *   `--batch`: Convert a directory of XLabel PNGs.
                *   For COCO: Creates a single aggregated COCO JSON file.
                *   For VOC/YOLO: Creates individual annotation files in an output directory.
*   **Python Modules:**
    *   `xcreator.py`: Handles embedding metadata into PNGs.
    *   `xreader.py`: Handles reading metadata from XLabel PNGs.
    *   `xlabel_format_converters` (package):
        *   `coco_converter.py`
        *   `voc_converter.py`
        *   `yolo_converter.py`
        *   `common.py` (shared exceptions and constants)
*   **Supports:**
    *   Bounding boxes.
    *   Segmentation (polygons and Run-Length Encoding - RLE).
    *   Confidence scores.
    *   Custom key-value attributes per annotation.

## Installation / Dependencies

1.  **Python 3.x** is required.
2.  **Pillow (PIL Fork):** The primary dependency for image manipulation and PNG chunk handling.
    ```bash
    pip install Pillow
    ```
3.  Clone this repository or download the Python scripts.

## Usage (`xlabel_cli.py`)

The main tool is `xlabel_cli.py`. You can get help by running:
```bash
python xlabel_cli.py --help
python xlabel_cli.py <command> --help
python xlabel_cli.py <command> <subcommand> --help
```

### Examples

#### 1. Create an XLabel PNG (Single)

Given `image.jpg` and `annotation.json`:
```json
// annotation.json
{
    "image_properties": {
        "filename": "image.jpg", 
        "width": 0, 
        "height": 0 
    },
    "class_names": ["cat", "dog"],
    "annotations": [
        {
            "class_id": 0, 
            "bbox": [50, 50, 100, 120], 
            "score": 0.95,
            "segmentation": [[50,50, 150,50, 150,170, 50,170]], 
            "custom_attributes": {"occluded": false}
        },
        {
            "class_id": 1, 
            "bbox": [200, 80, 80, 90], 
            "score": 0.88
        }
    ]
}
```
Command:
```bash
python xlabel_cli.py create single image.jpg annotation.json output_image.xlabel.png
```
This creates `output_image.xlabel.png` with the annotation data embedded. (`width` and `height` in `image_properties` will be auto-populated from `image.jpg`).

#### 2. Create XLabel PNGs (Batch)

*   `./images/` contains `img1.png`, `img2.jpg`, ...
*   `./json_labels/` contains `img1.json`, `img2.json`, ... (filenames must match images, excluding extension)
*   `./output_xlabels/` is where XLabel PNGs will be saved.

Command:
```bash
python xlabel_cli.py create batch ./images/ ./json_labels/ ./output_xlabels/ --overwrite
```

#### 3. Read Metadata from an XLabel PNG (Single)

To console:
```bash
python xlabel_cli.py read single output_image.xlabel.png
```
To a JSON file:
```bash
python xlabel_cli.py read single output_image.xlabel.png --output-json extracted_meta.json
```

#### 4. Read Metadata (Batch)

*   `./input_xlabels/` contains `img1.xlabel.png`, `img2.xlabel.png`, ...
*   `./output_jsons/` is where extracted JSON files will be saved.

Command:
```bash
python xlabel_cli.py read batch ./input_xlabels/ ./output_jsons/
```

#### 5. Convert COCO to XLabel PNGs (Batch)

*   `annotations.coco.json` is your COCO annotation file.
*   `./coco_images/` contains the images referenced in the COCO file.
*   `./output_xlabels_from_coco/` is the output directory.

Command:
```bash
python xlabel_cli.py convert 2xlabel coco --batch \
    --input-coco annotations.coco.json \
    --input-image-dir ./coco_images/ \
    --output-xlabel-dir ./output_xlabels_from_coco/
```

#### 6. Convert XLabel PNGs to Aggregated COCO JSON (Batch)

*   `./my_xlabel_dataset/` contains your XLabel PNGs.
*   `output_dataset.coco.json` will be the single aggregated COCO file.

Command:
```bash
python xlabel_cli.py convert fromxlabel coco --batch \
    --input-xlabel-dir-conv ./my_xlabel_dataset/ \
    --output-coco output_dataset.coco.json
```

#### 7. Convert VOC XMLs to XLabel PNGs (Batch)

*   `./voc_images/` contains your images.
*   `./voc_annotations/` contains corresponding `*.xml` files.
*   `./output_xlabels_from_voc/` is the output directory.

Command:
```bash
python xlabel_cli.py convert 2xlabel voc --batch \
    --input-image-dir ./voc_images/ \
    --input-voc-dir ./voc_annotations/ \
    --output-xlabel-dir ./output_xlabels_from_voc/
```

#### 8. Convert XLabel PNGs to YOLO (Batch)

*   `./my_xlabel_dataset/` contains your XLabel PNGs.
*   `./yolo_output/` will store `*.txt` annotation files and a single `classes.txt`.

Command:
```bash
python xlabel_cli.py convert fromxlabel yolo --batch \
    --input-xlabel-dir-conv ./my_xlabel_dataset/ \
    --output-dir-conv ./yolo_output/ \
    --yolo-class-names-output ./yolo_output/classes.txt 
```
*(Note: For single conversions, use `--single` instead of `--batch` and provide single file paths as per `--help` for the specific command.)*


## Why PNG Custom Chunks?

While EXIF was an initial thought, PNG's chunk-based architecture is more suitable for embedding larger, structured binary data. Custom ancillary chunks (like `xlDa`) can be safely ignored by applications that don't understand them, ensuring the image remains viewable everywhere. This method also avoids the stricter size limitations and text-only nature of many EXIF tags.

## Project Structure

*   `xlabel_cli.py`: The main command-line interface.
*   `xcreator.py`: Module for creating XLabel PNGs (embedding metadata).
*   `xreader.py`: Module for reading XLabel metadata from PNGs.
*   `xlabel_format_converters/` (Package):
    *   `common.py`: Shared exceptions and constants.
    *   `coco_converter.py`: Handles COCO format conversions.
    *   `voc_converter.py`: Handles Pascal VOC XML conversions.
    *   `yolo_converter.py`: Handles YOLO text format conversions.
    *   `__init__.py`: Makes the directory a package and exports relevant functions/classes.

## Limitations & Considerations

*   **Chunk Size:** While PNG chunks can be large (up to 2^31-1 bytes), embedding extremely verbose metadata (e.g., very complex segmentations for many objects) could significantly increase file size.
*   **PNG Specific:** This method is specific to the PNG format.
*   **Tooling:** Standard image viewers won't display the annotations. This toolkit is needed to access and utilize the embedded data.
*   **Modification by Other Tools:** Some aggressive image optimization tools *might* strip unknown custom chunks, though this is less common for ancillary chunks if correctly flagged.

## Future Ideas

*   Support for more annotation types (e.g., keypoints, polylines).
*   Integration with labeling tools.
*   A simple GUI wrapper.
*   Support for other image formats that allow custom metadata embedding.

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request.

---
*This project evolved from an experiment with EXIF tags to a more robust PNG custom chunk implementation for better data integrity and flexibility.*
