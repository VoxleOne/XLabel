"""
Handles conversion between XLabel's internal metadata format and Pascal VOC XML format.
"""
import xml.etree.ElementTree as ET
import os
import logging
from .common import XLabelConversionError, REFINED_METADATA_VERSION

logger = logging.getLogger(__name__)

def _add_xml_sub_element(parent, name, text):
    sub = ET.SubElement(parent, name)
    if text is not None:
        sub.text = str(text)
    return sub

def xlabel_metadata_to_voc_xml_tree(xlabel_data, default_folder="Unknown", default_database="Unknown"):
    """
    Converts XLabel metadata to a Pascal VOC XML ElementTree.
    """
    if not xlabel_data: raise XLabelConversionError("No xlabel_data provided to VOC exporter.")
    img_props = xlabel_data.get("image_properties")
    if not isinstance(img_props, dict): raise XLabelConversionError("VOC Export: 'image_properties' missing or not a dictionary.")
    if not all(k in img_props for k in ["filename", "width", "height"]): raise XLabelConversionError("VOC Export: 'image_properties' missing 'filename', 'width', or 'height'.")
    if not (isinstance(img_props["width"], int) and img_props["width"] > 0 and isinstance(img_props["height"], int) and img_props["height"] > 0):
        raise XLabelConversionError("VOC Export: 'image_properties' width/height must be positive integers.")
    root = ET.Element("annotation")
    _add_xml_sub_element(root, "folder", default_folder)
    _add_xml_sub_element(root, "filename", img_props["filename"])
    _add_xml_sub_element(root, "path", img_props.get("path", img_props["filename"]))
    source_node = _add_xml_sub_element(root, "source", None); _add_xml_sub_element(source_node, "database", default_database)
    size_node = _add_xml_sub_element(root, "size", None)
    _add_xml_sub_element(size_node, "width", img_props["width"]); _add_xml_sub_element(size_node, "height", img_props["height"])
    _add_xml_sub_element(size_node, "depth", img_props.get("depth", 3)); _add_xml_sub_element(root, "segmented", img_props.get("segmented", 0))
    class_names = xlabel_data.get("class_names", [])
    if not isinstance(class_names, list): raise XLabelConversionError("VOC Export: 'class_names' must be a list.")
    for ann_idx, ann in enumerate(xlabel_data.get("annotations", [])):
        if not isinstance(ann, dict): logger.warning(f"VOC Export: Annotation {ann_idx} is not a dict. Skipping."); continue
        class_id = ann.get("class_id"); bbox = ann.get("bbox")
        if not (isinstance(class_id, int) and 0 <= class_id < len(class_names)): logger.warning(f"VOC Export: Ann {ann_idx} invalid class_id: {class_id}. Skipping."); continue
        object_class_name = class_names[class_id]
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(c, (int, float)) for c in bbox)):
            logger.warning(f"VOC Export: Ann {ann_idx} (class {object_class_name}) invalid bbox: {bbox}. Skipping."); continue
        xmin, ymin, width, height = [int(c) for c in bbox]
        if width <= 0 or height <= 0: logger.warning(f"VOC Export: Ann {ann_idx} (class {object_class_name}) non-positive bbox width/height from {bbox}. Skipping."); continue
        xmax = xmin + width; ymax = ymin + height
        obj_node = _add_xml_sub_element(root, "object", None); _add_xml_sub_element(obj_node, "name", object_class_name)
        custom_attrs = ann.get("custom_attributes", {}); 
        if not isinstance(custom_attrs, dict): custom_attrs = {}
        _add_xml_sub_element(obj_node, "pose", custom_attrs.get("voc_pose", "Unspecified"))
        _add_xml_sub_element(obj_node, "truncated", int(custom_attrs.get("voc_truncated", 0)))
        _add_xml_sub_element(obj_node, "difficult", int(custom_attrs.get("voc_difficult", 0)))
        bndbox_node = _add_xml_sub_element(obj_node, "bndbox", None)
        _add_xml_sub_element(bndbox_node, "xmin", xmin); _add_xml_sub_element(bndbox_node, "ymin", ymin)
        _add_xml_sub_element(bndbox_node, "xmax", xmax); _add_xml_sub_element(bndbox_node, "ymax", ymax)
    return root

def voc_to_xlabel_metadata(voc_xml_path):
    """
    Converts a Pascal VOC XML file to XLabel internal metadata.
    """
    try: tree = ET.parse(voc_xml_path); root = tree.getroot()
    except FileNotFoundError: logger.error(f"VOC XML file not found: '{voc_xml_path}'"); raise
    except ET.ParseError as e: logger.error(f"Could not parse VOC XML '{voc_xml_path}': {e}"); raise XLabelConversionError(f"Parsing VOC XML: {e}") from e
    except Exception as e: logger.error(f"Unexpected error reading VOC XML '{voc_xml_path}': {e}", exc_info=True); raise XLabelConversionError(f"Reading VOC XML: {e}") from e
    filename_node = root.find("filename")
    filename = filename_node.text if filename_node is not None and filename_node.text else os.path.basename(voc_xml_path).rsplit('.', 1)[0] + ".png"
    size_node = root.find("size")
    if size_node is None: raise XLabelConversionError(f"VOC XML '{voc_xml_path}' missing 'size' info.")
    width_node = size_node.find("width"); height_node = size_node.find("height")
    if width_node is None or height_node is None or not width_node.text or not height_node.text: raise XLabelConversionError(f"VOC XML '{voc_xml_path}' missing width/height in 'size'.")
    try: image_width = int(width_node.text); image_height = int(height_node.text)
    except ValueError as e: raise XLabelConversionError(f"VOC XML '{voc_xml_path}' non-integer width/height: {e}") from e
    if image_width <= 0 or image_height <= 0: raise XLabelConversionError(f"VOC XML '{voc_xml_path}' non-positive width/height.")
    image_properties = {"filename": filename, "width": image_width, "height": image_height}
    xlabel_annotations = []; xlabel_class_names = []; class_name_to_id_map = {}
    for obj_idx, obj_node in enumerate(root.findall("object")):
        class_name_node = obj_node.find("name")
        if class_name_node is None or not class_name_node.text: logger.warning(f"VOC object {obj_idx} missing class name. Skipping."); continue
        class_name = class_name_node.text
        if class_name not in class_name_to_id_map: xlabel_class_names.append(class_name); class_name_to_id_map[class_name] = len(xlabel_class_names) - 1
        class_id = class_name_to_id_map[class_name]
        bndbox_node = obj_node.find("bndbox")
        if bndbox_node is None: logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) missing bndbox. Skipping."); continue
        try:
            xmin = int(float(bndbox_node.findtext("xmin", "0"))); ymin = int(float(bndbox_node.findtext("ymin", "0")))
            xmax = int(float(bndbox_node.findtext("xmax", "0"))); ymax = int(float(bndbox_node.findtext("ymax", "0")))
        except (AttributeError, ValueError, TypeError) as e: logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) invalid bndbox coords: {e}. Skipping."); continue
        bbox_width = xmax - xmin; bbox_height = ymax - ymin
        if bbox_width <= 0 or bbox_height <= 0: logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) non-positive bbox dims. Skipping."); continue
        annotation = {"class_id": class_id, "bbox": [xmin, ymin, bbox_width, bbox_height]}
        custom_attrs = {}
        if obj_node.findtext("pose"): custom_attrs["voc_pose"] = obj_node.findtext("pose")
        try:
            if obj_node.findtext("truncated") is not None: custom_attrs["voc_truncated"] = bool(int(obj_node.findtext("truncated")))
            if obj_node.findtext("difficult") is not None: custom_attrs["voc_difficult"] = bool(int(obj_node.findtext("difficult")))
        except ValueError: logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) non-integer truncated/difficult. Ignoring.")
        if custom_attrs: annotation["custom_attributes"] = custom_attrs
        xlabel_annotations.append(annotation)
    return {"xlabel_version": REFINED_METADATA_VERSION, "image_properties": image_properties, "class_names": xlabel_class_names, "annotations": xlabel_annotations}
