# yolo_converter.py — MIT License
# Author: Eraldo Marques <eraldo.bernardo@gmail.com> — Created: 2025-06-16
# See LICENSE.txt for full terms. This header must be retained in redistributions.

"""
Handles conversion between XLabel's internal metadata format and YOLO text format.
"""
import os
import logging
from .common import XLabelConversionError, REFINED_METADATA_VERSION

logger = logging.getLogger(__name__)

def yolo_to_xlabel_metadata(yolo_txt_path, class_names_path, image_width, image_height, image_filename=None):
    """
    Converts YOLO annotations to XLabel internal metadata.
    """
    if not (isinstance(image_width, int) and image_width > 0 and isinstance(image_height, int) and image_height > 0):
        raise XLabelConversionError("(YOLO Import): Image width/height must be positive integers.")
    try:
        with open(class_names_path, 'r') as f: xlabel_class_names = [line.strip() for line in f if line.strip()]
        if not xlabel_class_names: raise XLabelConversionError(f"(YOLO Import): No class names in '{class_names_path}'.")
    except FileNotFoundError: logger.error(f"(YOLO Import): Class names file '{class_names_path}' not found."); raise
    except Exception as e: logger.error(f"(YOLO Import): Error reading class names file '{class_names_path}': {e}", exc_info=True); raise XLabelConversionError(f"Reading class names: {e}") from e
    xlabel_annotations = []
    try:
        with open(yolo_txt_path, 'r') as f:
            for line_num, line in enumerate(f):
                parts = line.strip().split()
                if len(parts) < 5: logger.warning(f"(YOLO Import): Line {line_num+1} in '{yolo_txt_path}' too few parts. Skipping."); continue
                try:
                    class_id = int(parts[0]); x_c_norm = float(parts[1]); y_c_norm = float(parts[2]); w_norm = float(parts[3]); h_norm = float(parts[4])
                    score = float(parts[5]) if len(parts) >= 6 else None
                except ValueError: logger.warning(f"(YOLO Import): Line {line_num+1} invalid numeric value. Skipping."); continue
                if not (0 <= class_id < len(xlabel_class_names)): logger.warning(f"(YOLO Import): Line {line_num+1} invalid class_id {class_id}. Skipping."); continue
                if not (0.0 <= x_c_norm <= 1.0 and 0.0 <= y_c_norm <= 1.0 and 0.0 <= w_norm <= 1.0 and 0.0 <= h_norm <= 1.0):
                    logger.warning(f"(YOLO Import): Line {line_num+1} out-of-range normalized coordinates. Skipping."); continue
                abs_w = w_norm * image_width; abs_h = h_norm * image_height
                abs_xmin = (x_c_norm * image_width)-(abs_w/2); abs_ymin = (y_c_norm * image_height)-(abs_h/2)
                ann = {"class_id": class_id, "bbox": [int(round(abs_xmin)), int(round(abs_ymin)), int(round(abs_w)), int(round(abs_h))]}
                if score is not None: ann["score"] = score
                xlabel_annotations.append(ann)
    except FileNotFoundError: logger.error(f"(YOLO Import): Annotation file '{yolo_txt_path}' not found."); raise
    except Exception as e: logger.error(f"(YOLO Import): Reading annotation file '{yolo_txt_path}': {e}", exc_info=True); raise XLabelConversionError(f"Reading YOLO TXT: {e}") from e
    img_fn = image_filename if image_filename else (os.path.basename(yolo_txt_path).rsplit('.', 1)[0] + ".jpg")
    return {"xlabel_version": REFINED_METADATA_VERSION, "image_properties": {"filename": img_fn, "width": image_width, "height": image_height}, "class_names": xlabel_class_names, "annotations": xlabel_annotations}

def xlabel_metadata_to_yolo_lines(xlabel_data, include_score=True, precision=6):
    """
    Converts XLabel metadata to a list of YOLO format annotation lines.
    """
    if not xlabel_data: raise XLabelConversionError("(YOLO Export): No xlabel_data provided.")
    img_props = xlabel_data.get("image_properties")
    if not isinstance(img_props, dict): raise XLabelConversionError("(YOLO Export): Missing 'image_properties'.")
    w = img_props.get("width"); h = img_props.get("height")
    if not (isinstance(w, int) and w > 0 and isinstance(h, int) and h > 0): raise XLabelConversionError(f"(YOLO Export): Invalid image width/height: w={w}, h={h}.")
    yolo_lines = []
    for ann_idx, ann in enumerate(xlabel_data.get("annotations", [])):
        if not isinstance(ann, dict): logger.warning(f"(YOLO Export): Ann {ann_idx} not a dict. Skipping."); continue
        cid = ann.get("class_id"); bbox = ann.get("bbox")
        if not isinstance(cid, int): logger.warning(f"(YOLO Export): Ann {ann_idx} invalid class_id. Skipping."); continue
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(c, (int, float)) for c in bbox)):
            logger.warning(f"(YOLO Export): Ann {ann_idx} (class_id {cid}) invalid bbox. Skipping."); continue
        x,y,bw,bh = [int(c) for c in bbox]
        if bw <= 0 or bh <= 0: logger.warning(f"(YOLO Export): Ann {ann_idx} (class_id {cid}) non-positive bbox dims. Skipping."); continue
        x_c_n=max(0.0,min(1.0,(x+bw/2)/w)); y_c_n=max(0.0,min(1.0,(y+bh/2)/h))
        w_n=max(0.0,min(1.0,bw/w)); h_n=max(0.0,min(1.0,bh/h))
        parts = [str(cid),f"{x_c_n:.{precision}f}",f"{y_c_n:.{precision}f}",f"{w_n:.{precision}f}",f"{h_n:.{precision}f}"]
        if include_score and "score" in ann:
            try: score_val = float(ann['score']); parts.append(f"{score_val:.{precision}f}")
            except (ValueError, TypeError): logger.warning(f"(YOLO Export): Ann {ann_idx} non-numeric score '{ann['score']}'. Ignoring.")
        yolo_lines.append(" ".join(parts))
    return yolo_lines
