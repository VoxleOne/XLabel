# XLabel v0.3: Self-Contained Image Annotation Toolkit with GUI

XLabel is an open-source Python toolkit for embedding computer vision annotations directly into PNG image files as custom data chunks. With v0.3, **XLabel now features an intuitive graphical user interface (GUI)**, making the creation, editing, and management of annotated image datasets easier than ever. The GUI complements the robust command-line and programmatic workflows, offering a visual, user-friendly way to work with embedded image labels.

---

## Core Idea

Traditional computer vision datasets rely on separate sidecar files (JSON, XML, TXT) for image annotations, which can become disorganized or mismatched. XLabel solves this by embedding all annotation data directly inside the PNG file itself, using a custom chunk (`xlDa`, for "XLabel Data"). This keeps the image and its labels together in a single, portable file—now manageable via both CLI and GUI.

---

## Key Features

- **Graphical User Interface (GUI)**
  - Easily draw and edit bounding boxes and segmentations on images.
  - View, update, and manage annotation classes and custom attributes visually.
  - Import/export images and annotations via simple menus—no command-line needed.
  - Batch import/export and format conversion from the GUI.

- **Command-Line Interface (CLI)**
  - All v0.2 CLI features remain: create, read, and convert XLabel PNGs.
  - Seamless integration with the GUI: files edited in the GUI are CLI-compatible.

- **Multilayer Annotations**
  - Create and manage annotations that are compatible with multiple formats (COCO, VOC, YOLO) simultaneously within a single XLabel PNG.
  - Extend annotations with additional features or data (e.g., add custom attributes, segmentation polygons, or keypoints layers) to support complex workflows.

- **Format Conversion**
  - Convert between XLabel PNGs and standard formats (COCO, Pascal VOC, YOLO).
  - Export to and import from sidecar JSON, XML, or TXT files as needed.

- **Self-Contained Annotations**
  - All annotation data (classes, bounding boxes, segmentations, scores, etc.) travels with the image.
  - Classes, custom attributes, and segmentation data supported.

- **Batch Operations**
  - Process entire directories of images and labels via both CLI and GUI.

- **Educational and Research Use**
  - Demonstrates how structured metadata can be embedded within file formats.
  - Streamlines dataset curation for training and fine-tuning models.

---

## Typical Use Cases

- **Visual Dataset Curation:** Use the GUI to visually annotate images or inspect existing embedded labels.
- **Single-File Dataset Management:** Keep images and their labels together for small or proprietary datasets.
- **Format Bridging:** Export to or import from COCO, VOC, and YOLO for interoperability with other tools.
- **Dataset Integrity:** Reduce the risk of mismatches between images and annotations that can occur with sidecar files.

---

## Data Format

Annotations are stored within the PNG's `xlDa` chunk, as structured JSON. This includes:

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
  - PySide6
- Install with:
  ```bash
  pip install Pillow PySide6
  
  ```

- **Download:**  
  Clone this repository or download the release archive.

---

## Getting Started

### Launch the GUI

```bash
python xlabel_gui.py
```

- Open images or entire directories to annotate.
- Draw, edit, or remove bounding boxes and segmentations.
- Assign or create classes on the fly.
- Save to XLabel PNGs—annotations are embedded inside the images.
- Convert to/from COCO, VOC, or YOLO via the GUI's export/import menus.

### Using the CLI

All CLI commands from v0.2 are still supported and work seamlessly with GUI-created files.

```bash
python xlabel_cli.py --help
```

**Examples:**

- Batch create XLabel PNGs:
  ```bash
  python cli.py create batch ./images/ ./json_labels/ ./output_xlabels/
  ```
- Export embedded annotations to JSON sidecars:
  ```bash
  python cli.py read batch ./input_xlabels/ ./output_jsons/
  ```
- Convert COCO to XLabel PNGs:
  ```bash
  python cli.py convert 2xlabel coco --batch \
    --input-coco annotations.coco.json \
    --input-image-dir ./coco_images/ \
    --output-xlabel-dir ./output_xlabels_from_coco/
  ```
- Convert XLabel PNGs to aggregated COCO JSON:
  ```bash
  python cli.py convert fromxlabel coco --batch \
    --input-xlabel-dir-conv ./my_xlabel_dataset/ \
    --output-coco output_dataset.coco.json
  ```

---

## Project Structure

- `gui.py`: Graphical user interface application (NEW in v0.3)
- `cli.py`: Command-line interface.
- `creator.py`: Module for embedding metadata.
- `reader.py`: Module for reading embedded metadata.
- `xlabel_format_converters/`: Format conversion logic (COCO, VOC, YOLO).

---

## Limitations & Considerations

- **PNG specific:** Only works with PNG images.
- **Standard viewers:** Only the XLabel GUI displays annotations visually; standard image viewers ignore custom chunks.
- **File size:** Large or complex annotations may increase PNG file size.

---

## In The Works

- Support for more annotation types (e.g., keypoints, multi-labels).
- Multi-layer or multi-task annotations in a single XLabel PNG.
- Further enhancements to the GUI (zoom/pan, workflow improvements).

---

## Contributing

Contributions, bug reports, and feature requests are welcome!

---

XLabel now offers the best of both worlds: single-file, embedded annotations for simplicity and integrity, plus a modern GUI to make annotation and dataset management accessible to everyone.
****
