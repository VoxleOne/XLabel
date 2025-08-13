import os

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

    # Placeholders for other formats
    def to_coco(self, annotations: dict, image_path: str):
        # COCO export logic would go here
        print("COCO export not yet implemented.")
        return "{}"

    def to_pascal_voc(self, annotations: dict, image_path: str, image_width: int, image_height: int):
        # Pascal VOC export logic would go here
        print("Pascal VOC export not yet implemented.")
        return "<annotation></annotation>"
