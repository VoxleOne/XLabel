# XLabel: Self-Contained Image Annotations

**XLabel** is a Python toolkit for embedding computer vision annotations directly into PNG image files using custom data chunks. This approach simplifies dataset management by keeping images and their labels together in a single file. It also offers flexibility by allowing conversion to and from standard sidecar annotation formats.

The tool provides a command-line interface (`xlabel_cli.py`) and a set of Python modules to:
*   **Create** XLabel PNGs by embedding structured JSON metadata into images.
*   **Read** embedded metadata from XLabel PNGs, outputting to console or individual JSON sidecar files.
*   **Convert** between XLabel PNGs and common annotation formats (COCO, Pascal VOC, YOLO), supporting both single-file and batch operations.

## Core Idea & Why XLabel?

Computer Vision image labels are metadata. Instead of relying solely on external files that can get mismatched or lost, XLabel stores this metadata directly within the PNG image itself using a custom chunk type named `xlDa` (XLabel Data). This makes datasets more portable and easier to manage, while also providing bridges to traditional workflows.

**Key Use Cases & Benefits:**

*   **Simplified Dataset Management:** For smaller, proprietary, or research datasets, XLabel offers a streamlined, single-file-per-image approach, reducing the clutter of numerous sidecar files.
*   **Fine-Tuning Datasets:** Ideal for creating and managing small, specialized datasets for fine-tuning larger pre-trained models. For example, a dataset of "Zebu cattle" images (underrepresented in COCO) can be easily curated with XLabel to fine-tune a general "cow" detection model.
*   **Workflow Flexibility:**
    *   Work with self-contained XLabel PNGs for ease of transfer and storage.
    *   Easily **export embedded annotations back to individual JSON sidecar files** using the `read batch` command if a project requires them.
    *   Convert entire XLabel datasets to standard formats like COCO, VOC, or YOLO for compatibility with other tools and pipelines.
*   **Confidential Datasets:** While not a cryptographic solution, embedding data within the image can act as a mild layer of obfuscation, as the annotations are not immediately visible as separate files.
*   **Data Integrity:** Reduces the risk of mismatches between an image and its (separate) annotation file.
*   **Educational Purposes:** Provides a clear example of how metadata can be embedded within file formats.

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
*   **Sidecar File Compatibility:** Export embedded labels to individual JSON sidecar files.
*   **Format Conversion:**
    *   XLabel PNGs  <->  COCO JSON (single or aggregated)
    *   XLabel PNGs  <->  Pascal VOC XML
    *   XLabel PNGs  <->  YOLO text files (including `classes.txt`)
*   **CLI Tool (`xlabel_cli.py`):**
    *   `create`: Embed JSON annotations into images to create XLabel PNGs (single or batch).
    *   `read`: Extract embedded XLabel metadata.
        *   `single`: Output to console or a single JSON file.
        *   `batch`: **Export to individual JSON sidecar files** in an output directory.
    *   `convert`: Convert annotations between XLabel and other formats (single or batch).
*   **Python Modules:** `xcreator.py`, `xreader.py`, and the `xlabel_format_converters` package.
*   **Supports:** Bounding boxes, polygon segmentation, RLE segmentation, confidence scores, custom attributes.

## Installation / Dependencies

1.  **Python 3.x** is required.
2.  **Pillow (PIL Fork):**
    ```bash
    pip install Pillow
    ```
3.  Clone this repository or download the Python scripts.

## Usage (`xlabel_cli.py`)

Get help:
```bash
python xlabel_cli.py --help
python xlabel_cli.py <command> --help
python xlabel_cli.py <command> <subcommand> --help
```

### Key Examples

#### 1. Create XLabel PNGs (Batch)
From `./images/` and corresponding `./json_labels/` to `./output_xlabels/`:
```bash
python xlabel_cli.py create batch ./images/ ./json_labels/ ./output_xlabels/
```

#### 2. Export XLabel PNGs to JSON Sidecar Files (Batch)
From `./input_xlabels/` (containing XLabel PNGs) to `./output_jsons/` (containing individual `*.json` files):
```bash
python xlabel_cli.py read batch ./input_xlabels/ ./output_jsons/
```

#### 3. Convert COCO to XLabel PNGs (Batch)
From `annotations.coco.json` and `./coco_images/` to `./output_xlabels_from_coco/`:
```bash
python xlabel_cli.py convert 2xlabel coco --batch \
    --input-coco annotations.coco.json \
    --input-image-dir ./coco_images/ \
    --output-xlabel-dir ./output_xlabels_from_coco/
```

#### 4. Convert XLabel PNGs to Aggregated COCO JSON (Batch)
From `./my_xlabel_dataset/` to `output_dataset.coco.json`:
```bash
python xlabel_cli.py convert fromxlabel coco --batch \
    --input-xlabel-dir-conv ./my_xlabel_dataset/ \
    --output-coco output_dataset.coco.json
```
*(See `--help` for single file operations and other formats like VOC and YOLO.)*

## Why PNG Custom Chunks?
PNG's chunk architecture is ideal for embedding structured binary data. Custom ancillary chunks (like `xlDa`) are safely ignored by standard image viewers, ensuring compatibility, while avoiding the stricter limitations of EXIF tags.

## Project Structure
*   `xlabel_cli.py`: Main command-line interface.
*   `xcreator.py`: Module for embedding metadata.
*   `xreader.py`: Module for reading embedded metadata.
*   `xlabel_format_converters/`: Package for format conversion logic (COCO, VOC, YOLO).

## Limitations & Considerations
*   **PNG Specific:** This method is specific to the PNG format.
*   **Tooling:** Standard image viewers won't display annotations; this toolkit is needed.
*   **Chunk Size:** Very complex annotations could increase file size, though PNG chunks can be large.

## Future Ideas
*   GUI for visual annotation and management.
*   Support for more annotation types (keypoints, etc.).
*   Multi-layer annotations within a single XLabel PNG.

## Contributing
Contributions, bug reports, and feature requests are welcome!

---
*This project provides a flexible way to manage image annotations, either embedded directly for simplicity or exported to traditional sidecar files as needed.*
