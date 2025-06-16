import json
import datetime
import xml.etree.ElementTree as ET
import os
import logging

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# --- Custom Exceptions (can be shared or defined in a common module later) ---
class XLabelError(Exception):
    """Base class for exceptions related to XLabel processing."""
    pass

class XLabelFormatError(XLabelError):
    """Exception raised for errors in the XLabel data format or structure."""
    pass

class XLabelConversionError(XLabelError):
    """Exception for errors during format conversion."""
    pass

# --- Constants ---
CURRENT_XLABEL_VERSION = "0.1.0" # Base refined_metadata structure version
# Updated with user-provided information
CURRENT_DATE_TIME_UTC = "2025-06-16 15:47:23"
CURRENT_USER_LOGIN = "VoxleOne"


# ... (The rest of xlabel_converters.py remains the same as the previously refactored version)
# --- Helper for XML creation ---
def _add_xml_sub_element(parent, name, text):
    sub = ET.SubElement(parent, name)
    if text is not None:
        sub.text = str(text)
    return sub

# --- Pascal VOC Exporter (Bounding Box Focused) ---
def xlabel_metadata_to_voc_xml_tree(xlabel_data, default_folder="Unknown", default_database="Unknown"):
    if not xlabel_data:
        raise XLabelConversionError("No xlabel_data provided to VOC exporter.")

    img_props = xlabel_data.get("image_properties")
    if not isinstance(img_props, dict):
        raise XLabelConversionError("VOC Export: 'image_properties' missing or not a dictionary.")
    if not all(k in img_props for k in ["filename", "width", "height"]):
        raise XLabelConversionError("VOC Export: 'image_properties' missing 'filename', 'width', or 'height'.")
    if not (isinstance(img_props["width"], int) and img_props["width"] > 0 and
            isinstance(img_props["height"], int) and img_props["height"] > 0):
        raise XLabelConversionError("VOC Export: 'image_properties' width/height must be positive integers.")

    root = ET.Element("annotation")
    _add_xml_sub_element(root, "folder", default_folder)
    _add_xml_sub_element(root, "filename", img_props["filename"])
    _add_xml_sub_element(root, "path", img_props.get("path", img_props["filename"]))
    source_node = _add_xml_sub_element(root, "source", None)
    _add_xml_sub_element(source_node, "database", default_database)
    size_node = _add_xml_sub_element(root, "size", None)
    _add_xml_sub_element(size_node, "width", img_props["width"])
    _add_xml_sub_element(size_node, "height", img_props["height"])
    _add_xml_sub_element(size_node, "depth", img_props.get("depth", 3))
    _add_xml_sub_element(root, "segmented", img_props.get("segmented", 0))

    class_names = xlabel_data.get("class_names", [])
    if not isinstance(class_names, list):
        raise XLabelConversionError("VOC Export: 'class_names' must be a list.")

    for ann_idx, ann in enumerate(xlabel_data.get("annotations", [])):
        if not isinstance(ann, dict):
            logger.warning(f"VOC Export: Annotation {ann_idx} is not a dict. Skipping.")
            continue
        class_id = ann.get("class_id")
        bbox = ann.get("bbox")

        if not (isinstance(class_id, int) and 0 <= class_id < len(class_names)):
            logger.warning(f"VOC Export: Ann {ann_idx} invalid class_id: {class_id}. Skipping.")
            continue
        object_class_name = class_names[class_id]
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(c, (int, float)) for c in bbox)):
            logger.warning(f"VOC Export: Ann {ann_idx} (class {object_class_name}) invalid bbox: {bbox}. Skipping.")
            continue
        
        xmin, ymin, width, height = [int(c) for c in bbox] # Ensure integer coordinates for VOC
        if width <= 0 or height <= 0:
            logger.warning(f"VOC Export: Ann {ann_idx} (class {object_class_name}) non-positive bbox width/height from {bbox}. Skipping.")
            continue
        xmax = xmin + width
        ymax = ymin + height

        obj_node = _add_xml_sub_element(root, "object", None)
        _add_xml_sub_element(obj_node, "name", object_class_name)
        custom_attrs = ann.get("custom_attributes", {})
        if not isinstance(custom_attrs, dict): custom_attrs = {} # Ensure it's a dict
        _add_xml_sub_element(obj_node, "pose", custom_attrs.get("voc_pose", "Unspecified"))
        _add_xml_sub_element(obj_node, "truncated", int(custom_attrs.get("voc_truncated", 0)))
        _add_xml_sub_element(obj_node, "difficult", int(custom_attrs.get("voc_difficult", 0)))
        bndbox_node = _add_xml_sub_element(obj_node, "bndbox", None)
        _add_xml_sub_element(bndbox_node, "xmin", xmin)
        _add_xml_sub_element(bndbox_node, "ymin", ymin)
        _add_xml_sub_element(bndbox_node, "xmax", xmax)
        _add_xml_sub_element(bndbox_node, "ymax", ymax)
    return root

# --- Pascal VOC Importer (Bounding Box Focused) ---
def voc_to_xlabel_metadata(voc_xml_path):
    try:
        tree = ET.parse(voc_xml_path)
        root = tree.getroot()
    except FileNotFoundError:
        logger.error(f"VOC XML file not found at '{voc_xml_path}'")
        raise
    except ET.ParseError as e:
        logger.error(f"Could not parse VOC XML file '{voc_xml_path}': {e}")
        raise XLabelConversionError(f"Could not parse VOC XML: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error reading VOC XML '{voc_xml_path}': {e}", exc_info=True)
        raise XLabelConversionError(f"Unexpected error reading VOC XML: {e}") from e

    filename_node = root.find("filename")
    filename = filename_node.text if filename_node is not None and filename_node.text else os.path.basename(voc_xml_path).rsplit('.', 1)[0] + ".png"
    
    size_node = root.find("size")
    if size_node is None: raise XLabelConversionError(f"VOC XML '{voc_xml_path}' missing 'size' information.")
    width_node = size_node.find("width"); height_node = size_node.find("height")
    if width_node is None or height_node is None or not width_node.text or not height_node.text:
        raise XLabelConversionError(f"VOC XML '{voc_xml_path}' missing width/height values in 'size' node.")
    try:
        image_width = int(width_node.text); image_height = int(height_node.text)
    except ValueError as e:
        raise XLabelConversionError(f"VOC XML '{voc_xml_path}' has non-integer width/height: {e}") from e
    if image_width <= 0 or image_height <= 0:
        raise XLabelConversionError(f"VOC XML '{voc_xml_path}' has non-positive width/height.")
    
    image_properties = {"filename": filename, "width": image_width, "height": image_height}
    xlabel_annotations = []; xlabel_class_names = []; class_name_to_id_map = {}

    for obj_idx, obj_node in enumerate(root.findall("object")):
        class_name_node = obj_node.find("name")
        if class_name_node is None or not class_name_node.text:
            logger.warning(f"VOC object {obj_idx} in '{voc_xml_path}' missing class name. Skipping."); continue
        class_name = class_name_node.text
        if class_name not in class_name_to_id_map:
            xlabel_class_names.append(class_name)
            class_name_to_id_map[class_name] = len(xlabel_class_names) - 1
        class_id = class_name_to_id_map[class_name]
        
        bndbox_node = obj_node.find("bndbox")
        if bndbox_node is None:
            logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) in '{voc_xml_path}' missing bndbox. Skipping."); continue
        try:
            xmin = int(float(bndbox_node.findtext("xmin", "0"))); ymin = int(float(bndbox_node.findtext("ymin", "0")))
            xmax = int(float(bndbox_node.findtext("xmax", "0"))); ymax = int(float(bndbox_node.findtext("ymax", "0")))
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) invalid bndbox coordinates: {e}. Skipping."); continue
        
        bbox_width = xmax - xmin; bbox_height = ymax - ymin
        if bbox_width <= 0 or bbox_height <= 0:
            logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) non-positive bbox dims from ({xmin},{ymin},{xmax},{ymax}). Skipping."); continue
        
        annotation = {"class_id": class_id, "bbox": [xmin, ymin, bbox_width, bbox_height]}
        custom_attrs = {}
        if obj_node.findtext("pose"): custom_attrs["voc_pose"] = obj_node.findtext("pose")
        try: # Handle potential conversion errors for boolean-like fields
            if obj_node.findtext("truncated") is not None: custom_attrs["voc_truncated"] = bool(int(obj_node.findtext("truncated")))
            if obj_node.findtext("difficult") is not None: custom_attrs["voc_difficult"] = bool(int(obj_node.findtext("difficult")))
        except ValueError: logger.warning(f"VOC object '{class_name}' (idx {obj_idx}) has non-integer truncated/difficult. Ignoring.")
        if custom_attrs: annotation["custom_attributes"] = custom_attrs
        xlabel_annotations.append(annotation)
        
    return {"xlabel_version": CURRENT_XLABEL_VERSION, "image_properties": image_properties, "class_names": xlabel_class_names, "annotations": xlabel_annotations}

# --- YOLO Importer (Bounding Box Focused) ---
def yolo_to_xlabel_metadata(yolo_txt_path, class_names_path, image_width, image_height, image_filename=None):
    if not (isinstance(image_width, int) and image_width > 0 and isinstance(image_height, int) and image_height > 0):
        raise XLabelConversionError("(YOLO Import): Image width/height must be positive integers.")
    try:
        with open(class_names_path, 'r') as f: xlabel_class_names = [line.strip() for line in f if line.strip()]
        if not xlabel_class_names:
            raise XLabelConversionError(f"(YOLO Import): No class names found in '{class_names_path}'.")
    except FileNotFoundError:
        logger.error(f"(YOLO Import): Class names file '{class_names_path}' not found.")
        raise
    except Exception as e:
        logger.error(f"(YOLO Import): Error reading class names file '{class_names_path}': {e}", exc_info=True)
        raise XLabelConversionError(f"Error reading class names file '{class_names_path}': {e}") from e

    xlabel_annotations = []
    try:
        with open(yolo_txt_path, 'r') as f:
            for line_num, line in enumerate(f):
                parts = line.strip().split()
                if len(parts) < 5:
                    logger.warning(f"(YOLO Import): Line {line_num+1} in '{yolo_txt_path}' has too few parts ({len(parts)}). Expected at least 5. Skipping."); continue
                try:
                    class_id = int(parts[0]); x_c_norm = float(parts[1]); y_c_norm = float(parts[2]); w_norm = float(parts[3]); h_norm = float(parts[4])
                    score = float(parts[5]) if len(parts) >= 6 else None
                except ValueError:
                    logger.warning(f"(YOLO Import): Line {line_num+1} in '{yolo_txt_path}' contains invalid numeric value. Skipping."); continue
                
                if not (0 <= class_id < len(xlabel_class_names)):
                    logger.warning(f"(YOLO Import): Line {line_num+1} has invalid class_id {class_id} (max: {len(xlabel_class_names)-1}). Skipping."); continue
                if not (0.0 <= x_c_norm <= 1.0 and 0.0 <= y_c_norm <= 1.0 and 0.0 <= w_norm <= 1.0 and 0.0 <= h_norm <= 1.0):
                    logger.warning(f"(YOLO Import): Line {line_num+1} has out-of-range normalized coordinates [{x_c_norm},{y_c_norm},{w_norm},{h_norm}]. Values must be in [0,1]. Skipping."); continue
                
                abs_w = w_norm * image_width; abs_h = h_norm * image_height
                abs_xmin = (x_c_norm * image_width) - (abs_w / 2); abs_ymin = (y_c_norm * image_height) - (abs_h / 2)
                
                ann = {"class_id": class_id, "bbox": [int(round(abs_xmin)), int(round(abs_ymin)), int(round(abs_w)), int(round(abs_h))]}
                if score is not None: ann["score"] = score
                xlabel_annotations.append(ann)
    except FileNotFoundError:
        logger.error(f"(YOLO Import): Annotation file '{yolo_txt_path}' not found.")
        raise
    except Exception as e:
        logger.error(f"(YOLO Import): Error reading annotation file '{yolo_txt_path}': {e}", exc_info=True)
        raise XLabelConversionError(f"Error reading annotation file '{yolo_txt_path}': {e}") from e

    img_fn = image_filename if image_filename else (os.path.basename(yolo_txt_path).rsplit('.', 1)[0] + ".jpg")
    return {"xlabel_version": CURRENT_XLABEL_VERSION, "image_properties": {"filename": img_fn, "width": image_width, "height": image_height}, "class_names": xlabel_class_names, "annotations": xlabel_annotations}

# --- YOLO Exporter (Bounding Box Focused) ---
def xlabel_metadata_to_yolo_lines(xlabel_data, include_score=True, precision=6):
    if not xlabel_data: raise XLabelConversionError("(YOLO Export): No xlabel_data provided.")
    img_props = xlabel_data.get("image_properties")
    if not isinstance(img_props, dict): raise XLabelConversionError("(YOLO Export): Missing 'image_properties'.")
    w = img_props.get("width"); h = img_props.get("height")
    if not (isinstance(w, int) and w > 0 and isinstance(h, int) and h > 0):
        raise XLabelConversionError(f"(YOLO Export): Invalid image width/height in image_properties: w={w}, h={h}.")
    
    yolo_lines = []
    for ann_idx, ann in enumerate(xlabel_data.get("annotations", [])):
        if not isinstance(ann, dict):
            logger.warning(f"(YOLO Export): Annotation {ann_idx} is not a dict. Skipping."); continue
        cid = ann.get("class_id"); bbox = ann.get("bbox")
        if not isinstance(cid, int):
            logger.warning(f"(YOLO Export): Ann {ann_idx} missing or invalid class_id. Skipping."); continue
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(c, (int, float)) for c in bbox)):
            logger.warning(f"(YOLO Export): Ann {ann_idx} (class_id {cid}) missing or invalid bbox. Skipping."); continue
        
        x,y,bw,bh = [int(c) for c in bbox]
        if bw <= 0 or bh <= 0:
            logger.warning(f"(YOLO Export): Ann {ann_idx} (class_id {cid}) has non-positive bbox width/height. Skipping."); continue
        
        x_c_n=max(0.0, min(1.0, (x+bw/2)/w))
        y_c_n=max(0.0, min(1.0, (y+bh/2)/h))
        w_n=max(0.0, min(1.0, bw/w))
        h_n=max(0.0, min(1.0, bh/h))
        
        parts = [str(cid), f"{x_c_n:.{precision}f}", f"{y_c_n:.{precision}f}", f"{w_n:.{precision}f}", f"{h_n:.{precision}f}"]
        if include_score and "score" in ann:
            try: score_val = float(ann['score']); parts.append(f"{score_val:.{precision}f}")
            except (ValueError, TypeError): logger.warning(f"(YOLO Export): Ann {ann_idx} (class_id {cid}) non-numeric score '{ann['score']}'. Ignoring score.")
        yolo_lines.append(" ".join(parts))
    return yolo_lines

# --- COCO Exporter (Updated for Segmentation) ---
def xlabel_metadata_to_coco_json_structure(xlabel_data, initial_image_id=1, initial_category_id=1, initial_annotation_id=1):
    if not xlabel_data: raise XLabelConversionError("No xlabel_data provided to COCO exporter.")
    
    img_props = xlabel_data.get("image_properties", {})
    if not (isinstance(img_props, dict) and img_props.get("filename") and 
            isinstance(img_props.get("width"), int) and img_props.get("width") > 0 and
            isinstance(img_props.get("height"), int) and img_props.get("height") > 0):
        raise XLabelConversionError("COCO Export: xlabel_data missing or invalid image_properties.")

    class_names = xlabel_data.get("class_names", [])
    if not isinstance(class_names, list):
        raise XLabelConversionError("COCO Export: 'class_names' must be a list.")

    coco_output = {
        "info": {
            "description": "XLabel Export - COCO Format", "version": xlabel_data.get("xlabel_version", CURRENT_XLABEL_VERSION),
            "year": datetime.datetime.strptime(CURRENT_DATE_TIME_UTC, "%Y-%m-%d %H:%M:%S").year,
            "contributor": CURRENT_USER_LOGIN, "date_created": CURRENT_DATE_TIME_UTC.replace(" ", "T") + "Z"
        },
        "licenses": [{"id": 1, "name": "Unknown", "url": ""}], "images": [], "categories": [], "annotations": []
    }
    current_image_id = initial_image_id
    coco_output["images"].append({"id": current_image_id, "file_name": img_props["filename"], "width": img_props["width"], "height": img_props["height"], "license": 1, "date_captured": ""})
    
    xlabel_class_id_to_coco_cat_id = {}
    current_coco_category_id = initial_category_id
    for idx, class_name_str in enumerate(class_names):
        if not isinstance(class_name_str, str):
            logger.warning(f"COCO Export: Non-string class name at index {idx}: '{class_name_str}'. Skipping category creation for this.")
            continue
        coco_output["categories"].append({"id": current_coco_category_id, "name": class_name_str, "supercategory": "None"})
        xlabel_class_id_to_coco_cat_id[idx] = current_coco_category_id
        current_coco_category_id += 1
        
    current_coco_annotation_id = initial_annotation_id
    for ann_idx, ann in enumerate(xlabel_data.get("annotations", [])):
        if not isinstance(ann, dict):
            logger.warning(f"COCO Export: Annotation {ann_idx} is not a dict. Skipping."); continue
        class_id = ann.get("class_id"); bbox = ann.get("bbox")
        if not isinstance(class_id, int):
            logger.warning(f"COCO Export: Ann {ann_idx} missing or invalid class_id. Skipping."); continue
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(c, (int, float)) for c in bbox)):
            logger.warning(f"COCO Export: Ann {ann_idx} (class_id {class_id}) missing or invalid bbox. Skipping."); continue
        
        coco_category_id = xlabel_class_id_to_coco_cat_id.get(class_id)
        if coco_category_id is None:
            logger.warning(f"COCO Export: Ann {ann_idx} class_id {class_id} not in mapped COCO categories (perhaps due to invalid class_name). Skipping."); continue
        
        try: x_min, y_min, width, height = [float(c) for c in bbox]
        except (ValueError, TypeError): logger.warning(f"COCO Export: Ann {ann_idx} invalid bbox values {bbox}. Skipping."); continue
        if width <= 0 or height <= 0: logger.warning(f"COCO Export: Ann {ann_idx} non-positive bbox width/height from {bbox}. Skipping."); continue
            
        area = width * height
        coco_ann = {"id": current_coco_annotation_id, "image_id": current_image_id, "category_id": coco_category_id, "bbox": [x_min, y_min, width, height], "area": area, "iscrowd": 0}

        segmentation_data = ann.get("segmentation")
        if segmentation_data:
            if isinstance(segmentation_data, list): # Polygons
                valid_segmentation_parts = []
                for poly_idx, poly_part in enumerate(segmentation_data):
                    if isinstance(poly_part, list) and len(poly_part) >= 6 and len(poly_part) % 2 == 0:
                        try: valid_segmentation_parts.append([float(p) for p in poly_part])
                        except (ValueError, TypeError): logger.warning(f"COCO Export: Ann {ann_idx} poly part {poly_idx} non-numeric points: {poly_part}. Skipping part."); continue
                    else: logger.warning(f"COCO Export: Ann {ann_idx} invalid poly part {poly_idx}: {poly_part}. Skipping part.")
                if valid_segmentation_parts: coco_ann["segmentation"] = valid_segmentation_parts
                else: coco_ann["segmentation"] = []
            elif isinstance(segmentation_data, dict) and "rle_counts" in segmentation_data and "rle_size" in segmentation_data:
                rle_c = segmentation_data["rle_counts"]; rle_s = segmentation_data["rle_size"]
                if isinstance(rle_c, list) and all(isinstance(c, int) for c in rle_c) and \
                   isinstance(rle_s, list) and len(rle_s) == 2 and all(isinstance(s, int) and s >= 0 for s in rle_s):
                    coco_ann["segmentation"] = {"counts": rle_c, "size": rle_s}
                else: logger.warning(f"COCO Export: Ann {ann_idx} invalid RLE data. Skipping segmentation."); coco_ann["segmentation"] = []
            else: logger.warning(f"COCO Export: Ann {ann_idx} unknown segmentation format. Treating as bbox-only."); coco_ann["segmentation"] = []
        
        if "score" in ann:
            try: coco_ann["score"] = float(ann["score"])
            except (ValueError, TypeError): logger.warning(f"COCO Export: Ann {ann_idx} non-numeric score '{ann['score']}'. Ignoring.")
        custom_attrs = ann.get("custom_attributes", {})
        if isinstance(custom_attrs, dict) and "coco_iscrowd" in custom_attrs:
            try: coco_ann["iscrowd"] = int(custom_attrs["coco_iscrowd"])
            except (ValueError, TypeError): logger.warning(f"COCO Export: Ann {ann_idx} non-numeric coco_iscrowd. Using default.")
            
        coco_output["annotations"].append(coco_ann)
        current_coco_annotation_id += 1
    return coco_output

# --- COCO Importer (Updated for Segmentation) ---
def coco_to_xlabel_metadata(coco_json_path, target_image_filename):
    try:
        with open(coco_json_path, 'r') as f: coco_data = json.load(f)
    except FileNotFoundError: logger.error(f"COCO JSON file not found: '{coco_json_path}'."); raise
    except json.JSONDecodeError as e: logger.error(f"Error decoding COCO JSON '{coco_json_path}': {e}"); raise XLabelConversionError(f"Decoding COCO JSON: {e}") from e
    except Exception as e: logger.error(f"Unexpected error reading COCO JSON '{coco_json_path}': {e}", exc_info=True); raise XLabelConversionError(f"Reading COCO JSON: {e}") from e

    if not isinstance(coco_data.get("images"), list): raise XLabelConversionError("COCO data 'images' field missing or not a list.")
    target_image_info = next((img for img in coco_data["images"] if img.get("file_name") == target_image_filename), None)
    if not target_image_info: raise XLabelConversionError(f"Image '{target_image_filename}' not found in COCO images list.")
        
    target_image_id = target_image_info.get("id")
    image_width = target_image_info.get("width"); image_height = target_image_info.get("height")
    if target_image_id is None or not (isinstance(image_width, int) and image_width > 0 and isinstance(image_height, int) and image_height > 0):
        raise XLabelConversionError(f"Target image '{target_image_filename}' info missing id or has invalid width/height.")

    xlabel_class_names = []; coco_cat_id_to_xlabel_class_id = {}
    if isinstance(coco_data.get("categories"), list):
        for category in coco_data["categories"]:
            cat_name = category.get("name"); cat_id = category.get("id")
            if isinstance(cat_name, str) and cat_name and cat_id is not None: # cat_id can be 0
                if cat_name not in xlabel_class_names: xlabel_class_names.append(cat_name)
                coco_cat_id_to_xlabel_class_id[cat_id] = xlabel_class_names.index(cat_name)
            else: logger.warning(f"COCO Import: Invalid category data: {category}. Skipping.")
    
    xlabel_annotations = []
    if isinstance(coco_data.get("annotations"), list):
        for ann_idx, coco_ann in enumerate(coco_data["annotations"]):
            if not isinstance(coco_ann, dict) or coco_ann.get("image_id") != target_image_id: continue
            
            internal_class_id = coco_cat_id_to_xlabel_class_id.get(coco_ann.get("category_id"))
            if internal_class_id is None: logger.warning(f"COCO Import: Ann {ann_idx} category_id '{coco_ann.get('category_id')}' not mapped. Skipping."); continue
            
            bbox_coco = coco_ann.get("bbox")
            if not (isinstance(bbox_coco, list) and len(bbox_coco) == 4): logger.warning(f"COCO Import: Ann {ann_idx} missing/invalid bbox. Skipping."); continue
            try:
                x,y,w,h = [float(c) for c in bbox_coco]
                if w <=0 or h <=0: logger.warning(f"COCO Import: Ann {ann_idx} non-positive w/h in bbox {bbox_coco}. Skipping."); continue
                bbox_xlabel = [int(round(x)), int(round(y)), int(round(w)), int(round(h))]
            except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} invalid bbox values {bbox_coco}. Skipping."); continue
            
            annotation = {"class_id": internal_class_id, "bbox": bbox_xlabel}
            coco_segmentation = coco_ann.get("segmentation")
            if coco_segmentation:
                if isinstance(coco_segmentation, list) and len(coco_segmentation) > 0:
                    valid_polygons = []
                    for poly_idx, poly_part in enumerate(coco_segmentation):
                        if isinstance(poly_part, list) and len(poly_part) >= 6 and len(poly_part) % 2 == 0:
                            try: valid_polygons.append([float(p) for p in poly_part])
                            except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} poly part {poly_idx} non-numeric points: {poly_part}. Skipping part."); continue
                        else: logger.warning(f"COCO Import: Ann {ann_idx} invalid poly part {poly_idx}: {poly_part}. Skipping part.")
                    if valid_polygons: annotation["segmentation"] = valid_polygons
                elif isinstance(coco_segmentation, dict) and "counts" in coco_segmentation and "size" in coco_segmentation:
                    rle_c = coco_segmentation["counts"]; rle_s = coco_segmentation["size"]
                    if isinstance(rle_c, list) and (all(isinstance(c, int) for c in rle_c) or all(isinstance(c, float) for c in rle_c)) and \
                       isinstance(rle_s, list) and len(rle_s) == 2 and all(isinstance(s, int) and s >=0 for s in rle_s):
                        annotation["segmentation"] = {"rle_counts": [int(c) for c in rle_c], "rle_size": rle_s}
                    else: logger.warning(f"COCO Import: Ann {ann_idx} invalid RLE data. Skipping segmentation.")
            
            if "score" in coco_ann:
                try: annotation["score"] = float(coco_ann["score"])
                except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} non-numeric score '{coco_ann['score']}'. Ignoring.")
            custom_attrs = {}
            if "id" in coco_ann: custom_attrs["coco_annotation_id"] = coco_ann["id"]
            if "iscrowd" in coco_ann:
                try: custom_attrs["coco_iscrowd"] = int(coco_ann["iscrowd"])
                except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} non-numeric iscrowd. Ignoring.")
            if custom_attrs: annotation["custom_attributes"] = custom_attrs
            xlabel_annotations.append(annotation)

    return {"xlabel_version": CURRENT_XLABEL_VERSION, "image_properties": {"filename": target_image_filename, "width": image_width, "height": image_height}, "class_names": xlabel_class_names, "annotations": xlabel_annotations}

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Test cases remain largely the same, but now functions will raise exceptions on critical errors
    # instead of just returning None or printing. The __main__ block's try-excepts should catch these.

    # --- COCO Importer/Exporter Test with Segmentation ---
    logger.info("--- COCO Importer/Exporter Test (with Segmentation) ---")
    dummy_coco_seg_data = { # Same data as before
        "info": {"description": "Test COCO with Segmentation"},
        "images": [{"id": 201, "file_name": "seg_image.png", "width": 800, "height": 600}],
        "categories": [{"id": 1, "name": "shape"}, {"id": 2, "name": "object"}],
        "annotations": [
            {"id": 101, "image_id": 201, "category_id": 1, "bbox": [10,10,50,50], "segmentation": [[10,10,60,10,60,60,10,60]], "area": 2500, "iscrowd": 0, "score": 0.9},
            {"id": 102, "image_id": 201, "category_id": 2, "bbox": [100,100,120,80], "segmentation": {"counts": [20,15,50,25,1000], "size": [600,800]}, "area": 9600, "iscrowd": 0, "score": 0.85},
            {"id": 103, "image_id": 201, "category_id": 1, "bbox": [200,200,30,30], "area": 900, "iscrowd": 0}
        ]}
    dummy_coco_seg_path = "dummy_coco_seg_annotations.json"
    try:
        with open(dummy_coco_seg_path, 'w') as f: json.dump(dummy_coco_seg_data, f, indent=2)
        logger.info(f"Created dummy COCO with segmentation: '{dummy_coco_seg_path}'")
        
        imported_xlabel_data_seg = coco_to_xlabel_metadata(dummy_coco_seg_path, "seg_image.png")
        logger.info("COCO Importer (with Segmentation): Success (function completed).")
        # ... (further checks on imported_xlabel_data_seg as before) ...
            
        coco_json_output_seg = xlabel_metadata_to_coco_json_structure(imported_xlabel_data_seg)
        logger.info("COCO Exporter (with Segmentation): Success (function completed).")
        output_coco_path = "exported_from_xlabel_seg.json"
        with open(output_coco_path, 'w') as f_out: json.dump(coco_json_output_seg, f_out, indent=2)
        logger.info(f"Saved full COCO export with segmentation to '{output_coco_path}'")

    except XLabelConversionError as xce:
        logger.error(f"COCO Test: XLabelConversionError: {xce}", exc_info=True)
    except FileNotFoundError:
        logger.error(f"COCO Test: File not found (likely dummy file).", exc_info=True)
    except Exception as e:
        logger.error(f"COCO Test: Unexpected error: {e}", exc_info=True)

    # --- Pascal VOC Importer/Exporter Test ---
    logger.info(f"--- VOC Importer/Exporter Test (Bounding Box) ---")
    dummy_voc_xml_content = ("<annotation><filename>example_voc.jpg</filename><size><width>800</width><height>600</height></size>"
                           "<object><name>cat</name><bndbox><xmin>100</xmin><ymin>150</ymin><xmax>300</xmax><ymax>450</ymax></bndbox></object></annotation>")
    dummy_voc_xml_path = "dummy_voc_annotation_main.xml"
    try:
        with open(dummy_voc_xml_path, 'w') as f: f.write(dummy_voc_xml_content)
        imported_xlabel_voc = voc_to_xlabel_metadata(dummy_voc_xml_path)
        logger.info("VOC Importer: Success.")
        exported_voc_tree = xlabel_metadata_to_voc_xml_tree(imported_xlabel_voc)
        if exported_voc_tree is not None: logger.info("VOC Exporter: Success.")
        else: logger.error("VOC Exporter: Failed (returned None).") # Should ideally raise if critical
    except XLabelConversionError as xce: logger.error(f"VOC Test: XLabelConversionError: {xce}", exc_info=True)
    except Exception as e: logger.error(f"VOC Test: Unexpected error: {e}", exc_info=True)


    # --- YOLO Importer/Exporter Test ---
    logger.info(f"--- YOLO Importer/Exporter Test (Bounding Box) ---")
    dummy_yolo_classes = "person\nbicycle"; dummy_yolo_classes_path = "dummy_yolo_classes_main.txt"
    dummy_yolo_txt_in = "0 0.5 0.5 0.2 0.3 0.95\n1 0.25 0.25 0.1 0.15"; dummy_yolo_txt_path_in = "dummy_yolo_in_main.txt"
    try:
        with open(dummy_yolo_classes_path, 'w') as f: f.write(dummy_yolo_classes)
        with open(dummy_yolo_txt_path_in, 'w') as f: f.write(dummy_yolo_txt_in)
        imported_xlabel_yolo = yolo_to_xlabel_metadata(dummy_yolo_txt_path_in, dummy_yolo_classes_path, 1920, 1080, "yolo_img.jpg")
        logger.info("YOLO Importer: Success.")
        exported_yolo_lines = xlabel_metadata_to_yolo_lines(imported_xlabel_yolo)
        if exported_yolo_lines: logger.info(f"YOLO Exporter: Success. Generated {len(exported_yolo_lines)} lines.")
        else: logger.warning("YOLO Exporter: Generated no lines (or returned empty list).") # Might be valid if no annotations
    except XLabelConversionError as xce: logger.error(f"YOLO Test: XLabelConversionError: {xce}", exc_info=True)
    except Exception as e: logger.error(f"YOLO Test: Unexpected error: {e}", exc_info=True)
