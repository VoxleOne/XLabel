# XLabel: A Command-Line Toolkit for Self-Contained Image Annotations

<!--
README generated for user: VoxleOne
Date: 2025-07-29 19:07:18 UTC
-->

XLabel is an open-source Python toolkit for embedding computer vision annotations directly into PNG image files as custom data chunks. This project provides a robust command-line interface (CLI) and a set of modules to create, manage, and convert annotated image datasets programmatically.

---

## Core Idea

Traditional computer vision datasets rely on separate sidecar files (JSON, XML, TXT) for image annotations, which can become disorganized or mismatched. XLabel solves this by embedding all annotation data directly inside the PNG file itself, using a custom chunk (`xlDa`, for "XLabel Data"). This keeps the image and its labels together in a single, portable file, manageable entirely through the command line.

---

## Key Features

- **Command-Line Interface (CLI)**
  - A comprehensive CLI for all annotation management tasks: create, read, and convert XLabel PNGs from the terminal.
  - Designed for scripting and integration into automated data processing pipelines.

- **Multilayer Annotations**
  - Create and manage annotations that are compatible with multiple formats (COCO, VOC, YOLO) simultaneously within a single XLabel PNG.
  - Extend annotations with additional features or data (e.g., add custom attributes, segmentation polygons, or keypoints layers) to support complex workflows.

- **Powerful Format Conversion**
  - Convert between XLabel PNGs and standard formats like **COCO**, **Pascal VOC**, and **YOLO**.
  - Export embedded data to sidecar JSON, XML, or TXT files, and import from them to create XLabel PNGs.

- **Self-Contained Annotations**
  - All annotation data (classes, bounding boxes, segmentations, scores, etc.) travels with the image.
  - Supports classes, custom attributes, and segmentation data.

- **Batch Operations**
  - Process entire directories of images and labels with single commands, ideal for large datasets.

- **Educational and Research Use**
  - Demonstrates how structured metadata can be embedded within file formats.
  - Streamlines dataset curation for training and fine-tuning models in a scriptable environment.

---

## Typical Use Cases

- **Automated Dataset Pipelines:** Integrate XLabel into scripts for automated data preparation and augmentation.
- **Single-File Dataset Management:** Keep images and their labels together for small or proprietary datasets, ensuring portability and integrity.
- **Format Bridging:** Use the CLI to convert between COCO, VOC, and YOLO to ensure interoperability with various training frameworks.
- **Dataset Integrity:** Reduce the risk of mismatches between images and annotations that can occur with sidecar files.

---

## Data Format

Annotations are stored within the PNG's `xlDa` chunk as structured JSON. This includes:

- XLabel format version string.
- Image properties (original filename, width, height).
- List of class names.
- Annotations (per object):
  - `class_id` (index into classes)
  - `bbox`: [xmin, ymin, width, height]
  - Optional: confidence score, segmentation (polygon/RLE), custom attributes.

---

## Installation

- **Python 3.x** required.
- **Dependencies:**
  - Pillow
- Install with:
  ```bash
  pip install Pillow
  ```

- **Download:**
  Clone this repository or download the release archive.

---

## Getting Started with the CLI

All functionality is accessed through `cli.py`. To see the available commands, run:

```bash
python cli.py --help
```

### Examples:

- **Batch create XLabel PNGs from images and JSON labels:**
  ```bash
  python cli.py create batch ./images/ ./json_labels/ ./output_xlabels/
  ```

- **Export embedded annotations to JSON sidecar files:**
  ```bash
  python cli.py read batch ./input_xlabels/ ./output_jsons/
  ```

- **Convert a COCO dataset to XLabel PNGs:**
  ```bash
  python cli.py convert 2xlabel coco --batch \
    --input-coco annotations.coco.json \
    --input-image-dir ./coco_images/ \
    --output-xlabel-dir ./output_xlabels_from_coco/
  ```

- **Convert a directory of XLabel PNGs to an aggregated COCO JSON file:**
  ```bash
  python cli.py convert fromxlabel coco --batch \
    --input-xlabel-dir-conv ./my_xlabel_dataset/ \
    --output-coco output_dataset.coco.json
  ```

---

## Project Structure

- `cli.py`: Command-line interface.
- `creator.py`: Module for embedding metadata into PNGs.
- `reader.py`: Module for reading embedded metadata from PNGs.
- `xlabel_format_converters/`: Logic for format conversions (COCO, VOC, YOLO).

---

## Limitations & Considerations

- **PNG Specific:** Only works with PNG images.
- **Standard Viewers:** Standard image viewers will render the image but ignore the custom annotation data.
- **File Size:** Large or complex annotations may increase the PNG file size.

---

## In The Works

- Support for more annotation types (e.g., keypoints, multi-labels).
- Multi-layer or multi-task annotations in a single XLabel PNG.
- Performance enhancements for batch processing large-scale datasets.

---

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request.
