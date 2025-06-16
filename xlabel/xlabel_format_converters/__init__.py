"""
XLabel Format Converters Package.

This package provides utilities to convert XLabel's internal metadata format
to and from other common annotation formats like COCO, Pascal VOC, and YOLO.
"""

# Re-export custom exceptions so they can be imported from the package root
from .common import XLabelError, XLabelFormatError, XLabelConversionError, REFINED_METADATA_VERSION

# Re-export converter functions
from .coco_converter import (
    coco_to_xlabel_metadata, 
    xlabel_metadata_to_coco_parts, # Renamed from ...to_coco_json_structure
    update_coco_creation_timestamp, 
    update_coco_contributor
)
from .voc_converter import (
    voc_to_xlabel_metadata, 
    xlabel_metadata_to_voc_xml_tree
)
from .yolo_converter import (
    yolo_to_xlabel_metadata, 
    xlabel_metadata_to_yolo_lines
)

__all__ = [
    # Exceptions
    "XLabelError", "XLabelFormatError", "XLabelConversionError",
    # Constants
    "REFINED_METADATA_VERSION",
    # COCO functions
    "coco_to_xlabel_metadata", "xlabel_metadata_to_coco_parts",
    "update_coco_creation_timestamp", "update_coco_contributor",
    # VOC functions
    "voc_to_xlabel_metadata", "xlabel_metadata_to_voc_xml_tree",
    # YOLO functions
    "yolo_to_xlabel_metadata", "xlabel_metadata_to_yolo_lines",
]