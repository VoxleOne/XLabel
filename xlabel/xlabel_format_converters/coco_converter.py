# coco_converter.py — MIT License
# Author: Eraldo Marques <eraldo.bernardo@gmail.com> — Created: 2025-06-16
# See LICENSE.txt for full terms. This header must be retained in redistributions.

"""
Handles conversion between XLabel's internal metadata format and COCO JSON format.
"""
import json
import datetime
import logging
from .common import XLabelConversionError, REFINED_METADATA_VERSION # Import from within the package

logger = logging.getLogger(__name__)

# Constants specific to COCO export (info block)
# These are updated by the CLI based on user interaction context.
CURRENT_DATE_TIME_UTC = "2025-06-16 17:25:50" 
CURRENT_USER_LOGIN = "VoxleOne"


def coco_to_xlabel_metadata(coco_json_path, target_image_filename):
    """
    Converts annotations for a specific image from a COCO JSON file 
    to the XLabel internal metadata dictionary structure.
    """
    try:
        with open(coco_json_path, 'r') as f: coco_data = json.load(f)
    except FileNotFoundError: 
        logger.error(f"COCO JSON file not found: '{coco_json_path}'.")
        raise
    except json.JSONDecodeError as e: 
        logger.error(f"Error decoding COCO JSON '{coco_json_path}': {e}")
        raise XLabelConversionError(f"Decoding COCO JSON '{coco_json_path}': {e}") from e
    except Exception as e: 
        logger.error(f"Unexpected error reading COCO JSON '{coco_json_path}': {e}", exc_info=True)
        raise XLabelConversionError(f"Unexpected error reading COCO JSON '{coco_json_path}': {e}") from e

    if not isinstance(coco_data.get("images"), list): 
        raise XLabelConversionError("COCO data 'images' field missing or not a list.")
    
    target_image_info = next((img for img in coco_data["images"] if img.get("file_name") == target_image_filename), None)
    if not target_image_info: 
        raise XLabelConversionError(f"Image '{target_image_filename}' not found in COCO images list.")
        
    target_image_id = target_image_info.get("id")
    image_width = target_image_info.get("width")
    image_height = target_image_info.get("height")

    if target_image_id is None or \
       not (isinstance(image_width, int) and image_width > 0 and \
            isinstance(image_height, int) and image_height > 0):
        raise XLabelConversionError(f"Target image '{target_image_filename}' info is missing 'id' or has invalid 'width'/'height'.")

    xlabel_class_names = []
    coco_cat_id_to_xlabel_class_id = {}
    if isinstance(coco_data.get("categories"), list):
        for category in coco_data["categories"]:
            cat_name = category.get("name")
            cat_id = category.get("id")
            if isinstance(cat_name, str) and cat_name and cat_id is not None:
                if cat_name not in xlabel_class_names:
                    xlabel_class_names.append(cat_name)
                coco_cat_id_to_xlabel_class_id[cat_id] = xlabel_class_names.index(cat_name)
            else:
                logger.warning(f"COCO Import: Invalid category data encountered: {category}. Skipping.")
    
    xlabel_annotations = []
    if isinstance(coco_data.get("annotations"), list):
        for ann_idx, coco_ann in enumerate(coco_data["annotations"]):
            if not isinstance(coco_ann, dict) or coco_ann.get("image_id") != target_image_id:
                continue
            
            internal_class_id = coco_cat_id_to_xlabel_class_id.get(coco_ann.get("category_id"))
            if internal_class_id is None:
                logger.warning(f"COCO Import: Annotation {ann_idx} has category_id '{coco_ann.get('category_id')}' not found in mapped categories. Skipping."); continue
            
            bbox_coco = coco_ann.get("bbox") # [xmin, ymin, width, height]
            if not (isinstance(bbox_coco, list) and len(bbox_coco) == 4):
                logger.warning(f"COCO Import: Annotation {ann_idx} (category {internal_class_id}) missing or invalid bbox. Skipping."); continue
            try:
                x,y,w,h = [float(c) for c in bbox_coco]
                if w <=0 or h <=0: 
                    logger.warning(f"COCO Import: Annotation {ann_idx} (category {internal_class_id}) has non-positive width/height in bbox {bbox_coco}. Skipping."); continue
                bbox_xlabel = [int(round(x)), int(round(y)), int(round(w)), int(round(h))]
            except (ValueError, TypeError) as e:
                logger.warning(f"COCO Import: Annotation {ann_idx} (category {internal_class_id}) has invalid bbox values {bbox_coco}: {e}. Skipping."); continue
            
            annotation = {"class_id": internal_class_id, "bbox": bbox_xlabel}

            coco_segmentation = coco_ann.get("segmentation")
            if coco_segmentation:
                if isinstance(coco_segmentation, list) and len(coco_segmentation) > 0: # Polygon list
                    valid_polygons = []
                    for poly_idx, poly_part in enumerate(coco_segmentation):
                        if isinstance(poly_part, list) and len(poly_part) >= 6 and len(poly_part) % 2 == 0: # Min 3 points
                            try: valid_polygons.append([float(p) for p in poly_part])
                            except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} polygon part {poly_idx} contains non-numeric points: {poly_part}. Skipping part."); continue
                        else: logger.warning(f"COCO Import: Ann {ann_idx} polygon part {poly_idx} is invalid (e.g. too few points): {poly_part}. Skipping part.")
                    if valid_polygons: annotation["segmentation"] = valid_polygons
                
                elif isinstance(coco_segmentation, dict) and "counts" in coco_segmentation and "size" in coco_segmentation: # RLE
                    rle_counts = coco_segmentation["counts"]; rle_size = coco_segmentation["size"]
                    if isinstance(rle_counts, list) and \
                       (all(isinstance(c, int) for c in rle_counts) or all(isinstance(c, float) for c in rle_counts)) and \
                       isinstance(rle_size, list) and len(rle_size) == 2 and \
                       all(isinstance(s, int) and s >=0 for s in rle_size):
                        annotation["segmentation"] = {"rle_counts": [int(c) for c in rle_counts], "rle_size": rle_size} # Ensure counts are int
                    else:
                         logger.warning(f"COCO Import: Ann {ann_idx} has invalid RLE data structure. Skipping segmentation.")
            
            if "score" in coco_ann:
                try: annotation["score"] = float(coco_ann["score"])
                except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} has non-numeric score '{coco_ann['score']}'. Ignoring.")
            
            custom_attrs = {}
            if "id" in coco_ann: custom_attrs["coco_annotation_id"] = coco_ann["id"] # Store original COCO ann ID
            if "iscrowd" in coco_ann: 
                try: custom_attrs["coco_iscrowd"] = int(coco_ann["iscrowd"])
                except (ValueError, TypeError): logger.warning(f"COCO Import: Ann {ann_idx} non-numeric iscrowd. Ignoring.")
            if custom_attrs: annotation["custom_attributes"] = custom_attrs
            
            xlabel_annotations.append(annotation)

    return {
        "xlabel_version": REFINED_METADATA_VERSION, 
        "image_properties": {"filename": target_image_filename, "width": image_width, "height": image_height},
        "class_names": xlabel_class_names, 
        "annotations": xlabel_annotations,
    }


def xlabel_metadata_to_coco_parts(xlabel_data, current_image_id, category_map, current_max_category_id, current_annotation_id_start):
    """
    Converts a single xlabel_data object to COCO components for aggregation.
    """
    if not xlabel_data: raise XLabelConversionError("No xlabel_data to convert to COCO parts.")
    img_props = xlabel_data.get("image_properties", {})
    if not (img_props.get("filename") and isinstance(img_props.get("width"), int) and isinstance(img_props.get("height"), int)):
        raise XLabelConversionError("COCO Parts Export: xlabel_data missing or invalid image_properties (filename, width, height).")

    class_names = xlabel_data.get("class_names", []) 
    if not isinstance(class_names, list):
        raise XLabelConversionError("COCO Parts Export: 'class_names' must be a list.")

    image_coco_entry = {
        "id": current_image_id, "file_name": img_props["filename"],
        "width": img_props["width"], "height": img_props["height"],
        "license": 1, "date_captured": "" 
    }
    new_category_coco_entries = []
    local_class_id_to_global_coco_id = {} 

    for local_class_id, class_name_str in enumerate(class_names):
        if not isinstance(class_name_str, str):
            logger.warning(f"COCO Parts: Non-string class name '{class_name_str}' at local_id {local_class_id}. Skipping."); continue
        if class_name_str not in category_map:
            current_max_category_id += 1
            category_map[class_name_str] = current_max_category_id
            new_category_coco_entries.append({"id": current_max_category_id, "name": class_name_str, "supercategory": "None"})
        local_class_id_to_global_coco_id[local_class_id] = category_map[class_name_str]
        
    annotation_coco_entries = []
    next_annotation_id = current_annotation_id_start
    for ann_idx, ann_data in enumerate(xlabel_data.get("annotations", [])):
        if not isinstance(ann_data, dict): logger.warning(f"COCO Parts: Ann {ann_idx} not a dict. Skipping."); continue
        local_class_id = ann_data.get("class_id"); bbox = ann_data.get("bbox")
        if not isinstance(local_class_id, int) or local_class_id not in local_class_id_to_global_coco_id:
            logger.warning(f"COCO Parts: Ann {ann_idx} invalid/unmapped local_class_id {local_class_id}. Skipping."); continue
        global_coco_category_id = local_class_id_to_global_coco_id[local_class_id]
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(c, (int, float)) for c in bbox)):
            logger.warning(f"COCO Parts: Ann {ann_idx} (global_cat_id {global_coco_category_id}) invalid bbox. Skipping."); continue
        try: x_min, y_min, width, height = [float(b_val) for b_val in bbox]
        except (ValueError, TypeError): logger.warning(f"COCO Parts: Ann {ann_idx} invalid bbox values. Skipping."); continue
        if width <= 0 or height <= 0: logger.warning(f"COCO Parts: Ann {ann_idx} non-positive bbox dims. Skipping."); continue
        area = width * height
        coco_ann = {"id": next_annotation_id, "image_id": current_image_id, "category_id": global_coco_category_id,
                      "bbox": [x_min, y_min, width, height], "area": area, "iscrowd": 0}
        segmentation_data = ann_data.get("segmentation")
        if segmentation_data:
            if isinstance(segmentation_data, list): 
                valid_polygons = []
                for poly_part in segmentation_data:
                    if isinstance(poly_part, list) and len(poly_part) >= 6 and len(poly_part) % 2 == 0:
                        try: valid_polygons.append([float(p) for p in poly_part])
                        except: logger.warning(f"COCO Parts: Ann {ann_idx} poly part non-numeric. Skipping part."); continue
                    else: logger.warning(f"COCO Parts: Ann {ann_idx} invalid poly part. Skipping part.")
                if valid_polygons: coco_ann["segmentation"] = valid_polygons
                else: coco_ann["segmentation"] = [] 
            elif isinstance(segmentation_data, dict) and "rle_counts" in segmentation_data and "rle_size" in segmentation_data:
                rle_c = segmentation_data["rle_counts"]; rle_s = segmentation_data["rle_size"]
                if isinstance(rle_c, list) and all(isinstance(c, int) for c in rle_c) and \
                   isinstance(rle_s, list) and len(rle_s) == 2 and all(isinstance(s, int) and s>=0 for s in rle_s):
                    coco_ann["segmentation"] = {"counts": rle_c, "size": rle_s}
                else: logger.warning(f"COCO Parts: Ann {ann_idx} invalid RLE. Skipping segmentation."); coco_ann["segmentation"] = []
            else: logger.warning(f"COCO Parts: Ann {ann_idx} unknown segmentation. bbox-only."); coco_ann["segmentation"] = []
        if "score" in ann_data:
            try: coco_ann["score"] = float(ann_data["score"])
            except (ValueError, TypeError): logger.warning(f"COCO Parts: Ann {ann_idx} non-numeric score. Ignoring.")
        custom_attrs = ann_data.get("custom_attributes", {})
        if isinstance(custom_attrs, dict) and "coco_iscrowd" in custom_attrs:
            try: coco_ann["iscrowd"] = int(custom_attrs["coco_iscrowd"])
            except (ValueError, TypeError): logger.warning(f"COCO Parts: Ann {ann_idx} non-numeric coco_iscrowd. Using default.")
        annotation_coco_entries.append(coco_ann)
        next_annotation_id += 1
    return image_coco_entry, new_category_coco_entries, annotation_coco_entries, next_annotation_id, category_map, current_max_category_id

def update_coco_creation_timestamp(new_timestamp_utc):
    global CURRENT_DATE_TIME_UTC
    CURRENT_DATE_TIME_UTC = new_timestamp_utc
    logger.debug(f"COCO Converter: Timestamp updated to {CURRENT_DATE_TIME_UTC}")

def update_coco_contributor(new_user_login):
    global CURRENT_USER_LOGIN
    CURRENT_USER_LOGIN = new_user_login
    logger.debug(f"COCO Converter: Contributor updated to {CURRENT_USER_LOGIN}")
