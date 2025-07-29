# XLabel 🏷️

![XLabel GUI](https://user-images.githubusercontent.com/12345/placeholder.jpg)
*A placeholder image of the XLabel GUI in action. You can replace this with a real screenshot.*

---

**XLabel is a Python toolkit for embedding computer vision annotations directly into PNG image files using custom data chunks.** This approach simplifies dataset management by keeping images and their labels together in a single file, eliminating the need for separate "sidecar" annotation files (like JSON, XML, or TXT).

The project provides two primary tools:
1.  A feature-rich **graphical user interface (GUI)** for manual annotation.
2.  A versatile **command-line interface (CLI)** for batch processing and format conversion.

## Core Idea & Why XLabel?

Computer Vision image labels are metadata. Instead of relying on external files that can get mismatched or lost, XLabel stores this metadata directly within the PNG image itself using a custom chunk type named `xlDa` (XLabel Data). This makes datasets more portable, robust, and easier to manage.

### Key Use Cases:

*   **Smaller, Proprietary Datasets:** For research or internal projects where managing numerous sidecar files for a modest number of images becomes cumbersome, XLabel offers a streamlined, single-file-per-image approach.
*   **Fine-Tuning Datasets:** Ideal for creating and managing small, specialized datasets for fine-tuning larger pre-trained models. For example, a dataset of "Zebu cattle" images (underrepresented in COCO) can be easily curated with XLabel to fine-tune a general "cow" detection model.
*   **Confidential Datasets:** While not a cryptographic solution, embedding data within the image can act as a mild layer of obfuscation, as the annotations are not immediately visible as separate files. This can be useful in scenarios where data privacy is a concern.
*   **Simplified Data Transfer & Archival:** Bundling images and labels simplifies sharing, backup, and archival of datasets.
*   **Educational Purposes:** Provides a clear, practical example of how metadata can be embedded within file formats.

## Features

XLabel is designed to be a comprehensive solution for self-contained image annotation.

### GUI Features

*   **Multi-Mode Annotation:** Create different types of annotations in the same file.
    *   **Bounding Boxes:** For object detection.
    *   **Polygons:** For precise instance segmentation.
    *   **Pixel Masks:** For semantic segmentation, with brush and eraser tools.
    *   **Keypoints:** For pose estimation (planned).
*   **Interactive Viewer:** Smoothly pan and zoom, with clear rendering of active and completed annotations.
*   **Dockable Panels:** Manage annotation lists and class names in a clean, organized workspace.
*   **Direct-to-PNG Workflow:** Open a standard PNG, add labels, and save it back as an XLabel-enhanced PNG.

### Core & CLI Features (Planned)

*   **Create & Read:** Embed structured JSON metadata into PNGs and read it back programmatically.
*   **Rich Format Conversion:** Convert between the integrated XLabel PNG format and common annotation standards, including **COCO**, **Pascal VOC**, and **YOLO**.
*   **Sidecar Export:** Export embedded annotations back to traditional sidecar file structures (e.g., separate `.json` or `.xml` files) for compatibility with other tools.
*   **Batch Processing:** Scriptable operations for handling entire datasets at once.

## Installation

XLabel requires **Python 3.11** or newer.

To get started, clone the repository and install the required dependencies.

```bash
# Clone the repository
git clone https://github.com/your-username/xlabel.git
cd xlabel

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

The `requirements.txt` file should contain:

```text name=requirements.txt
PySide6
Pillow
```

## Usage

### XLabel Annotation GUI

To launch the graphical annotation tool, run `main.py`:

```bash
python -m xlabel.gui.main
```

**Workflow:**
1.  Go to `File > Open XLabel PNG...` to load an image.
2.  Select an annotation tool from the left-hand toolbar (Bounding Box, Polygon, or Mask).
3.  Create annotations directly on the image:
    *   **Bounding Box:** Click and drag to draw a box.
    *   **Polygon:** Click to place points. Right-click or press `Enter` to finalize the shape.
    *   **Mask:** Click and drag to paint with the brush. Use the `Brush` (B) and `Eraser` (E) modes for adjustments. Right-click or press `Enter` to finalize the mask.
4.  View and manage your annotations in the "Annotations" panel on the right.
5.  Go to `File > Save` or `File > Save As...` to save your work. The annotations will be embedded directly into the new PNG file.

### Command-Line Interface (CLI)

The `xlabel_cli.py` script will provide powerful batch-processing capabilities.

**(Note: The following examples are illustrative of planned features. Please refer to the script's help menu for exact commands and arguments once implemented.)**

**Example: Add metadata to a single image**
```bash
python xlabel_cli.py add --image my_image.png --json-data '{"class": "cat", "bbox": [10, 20, 50, 60]}'
```

**Example: Extract annotations from an XLabel PNG to a JSON file**
```bash
python xlabel_cli.py extract --image my_labeled_image.png --output-file annotations.json
```

**Example: Convert a directory of XLabel PNGs to COCO format**
```bash
python xlabel_cli.py convert --input-dir ./xlabel_dataset --output-file coco_dataset.json --format coco
```

## How It Works

XLabel leverages the Portable Network Graphics (PNG) specification, which allows for custom ancillary "chunks" to be stored within the file. We use a custom chunk with the type `xlDa` to hold a compressed JSON payload containing all annotation data. This ensures that the image remains a valid, viewable PNG file in any standard image viewer, while the metadata is readily available to tools that know how to look for it.

## Contributing

Contributions are welcome! If you have ideas for new features, bug fixes, or improvements, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
