import os
import json
from datetime import datetime

class Exporter:
    """Handles exporting annotations to various formats."""

    def to_yolo(self, annotations: dict, image_width: int, image_height: int) -> str:
        """
        Converts bounding box annotations to YOLO format string.

        Args:
            annotations (dict): The annotation data, expecting a 'bbox' key.
            image_width (int): The width of the source image.
            image_height (int): The height of the source image.

        Returns:
            str: A string with each line formatted for a YOLO .txt file.
                 Returns an empty string if there are no bounding boxes.
        """
        lines = []
        
        # YOLO format is primarily for bounding boxes
        bboxes = annotations.get('bbox', {}).get('completed', [])
        if not bboxes:
            return ""

        for bbox in bboxes:
            # Assuming class_index is 0 as we don't have class management yet
            class_index = 0
            
            # bbox is [x, y, width, height]
            x, y, w, h = bbox
            
            # YOLO format requires normalized center coordinates and dimensions
            x_center = x + w / 2
            y_center = y + h / 2
            
            norm_x = x_center / image_width
            norm_y = y_center / image_height
            norm_w = w / image_width
            norm_h = h / image_height
            
            lines.append(f"{class_index} {norm_x:.6f} {norm_y:.6f} {norm_w:.6f} {norm_h:.6f}")
            
        return "\n".join(lines)

    def to_coco(self, annotations: dict, image_path: str, image_width: int, image_height: int) -> str:
        """
        Converts annotations to COCO format for a single image.

        Args:
            annotations (dict): The annotation data.
            image_path (str): The path to the source image.
            image_width (int): The width of the source image.
            image_height (int): The height of the source image.

        Returns:
            str: A JSON string in COCO format.
        """
        now = datetime.utcnow()
        
        coco_output = {
            "info": {
                "year": now.year,
                "version": "1.0",
                "description": "Exported from XLabel",
                "contributor": "XLabel User",
                "url": "",
                "date_created": now.isoformat()
            },
            "licenses": [],
            "images": [{
                "id": 1,
                "width": image_width,
                "height": image_height,
                "file_name": os.path.basename(image_path),
            }],
            "annotations": [],
            "categories": [{
                "id": 1,
                "name": "object",
                "supercategory": "none"
            }]
        }

        annotation_id = 1

        # Process Bounding Boxes
        bboxes = annotations.get('bbox', {}).get('completed', [])
        for bbox in bboxes:
            x, y, w, h = bbox
            coco_output['annotations'].append({
                "id": annotation_id,
                "image_id": 1,
                "category_id": 1,
                "segmentation": [],  # Bbox doesn't have segmentation
                "area": float(w * h),
                "bbox": [float(x), float(y), float(w), float(h)],
                "iscrowd": 0
            })
            annotation_id += 1

        # Process Polygons
        polygons = annotations.get('polygon', {}).get('completed', [])
        for poly in polygons:
            segmentation = [coord for point in poly for coord in (point[0], point[1])]
            
            # Calculate area and bounding box for the polygon
            min_x = min(p[0] for p in poly)
            max_x = max(p[0] for p in poly)
            min_y = min(p[1] for p in poly)
            max_y = max(p[1] for p in poly)
            poly_w = max_x - min_x
            poly_h = max_y - min_y

            # A simple area calculation (shoelace formula is more accurate but complex)
            # For now, bounding box area is a reasonable approximation.
            area = poly_w * poly_h

            coco_output['annotations'].append({
                "id": annotation_id,
                "image_id": 1,
                "category_id": 1,
                "segmentation": [segmentation],
                "area": float(area),
                "bbox": [float(min_x), float(min_y), float(poly_w), float(poly_h)],
                "iscrowd": 0
            })
            annotation_id += 1
            
        return json.dumps(coco_output, indent=4)

    def to_pascal_voc(self, annotations: dict, image_path: str, image_width: int, image_height: int):
        # Pascal VOC export logic would go here
        print("Pascal VOC export not yet implemented.")
        return "<annotation></annotation>"
