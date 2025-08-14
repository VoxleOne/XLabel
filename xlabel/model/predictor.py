import random

class ModelPredictor:
    """
    A class to handle model inference for semi-automated annotation.
    This is a mock implementation and should be replaced with a real model loader.
    """
    def __init__(self, model_path: str):
        self.model_path = model_path
        print(f"ModelPredictor initialized for model: {model_path}")
        # --- REAL IMPLEMENTATION ---
        # from ultralytics import YOLO
        # self.model = YOLO(model_path)

    def predict(self, image_path: str, image_width: int, image_height: int, 
                confidence_threshold: float, iou_threshold: float) -> list:
        """
        Runs inference on a given image and returns predictions based on thresholds.
        """
        print(f"Running mock prediction with conf={confidence_threshold}, iou={iou_threshold}")
        # --- REAL IMPLEMENTATION ---
        # results = self.model(image_path, conf=confidence_threshold, iou=iou_threshold)
        # predictions = []
        # for r in results:
        #     for box in r.boxes:
        #         # ... (extraction logic) ...
        #         predictions.append({ ... "source": "model"})
        # return predictions

        # --- MOCK IMPLEMENTATION ---
        predictions = []
        for i in range(random.randint(5, 15)):
            confidence = round(random.uniform(0.25, 0.99), 2)
            # Filter by confidence threshold
            if confidence < confidence_threshold:
                continue

            w = random.randint(int(image_width * 0.1), int(image_width * 0.3))
            h = random.randint(int(image_height * 0.1), int(image_height * 0.3))
            x = random.randint(0, image_width - w)
            y = random.randint(0, image_height - h)
            predictions.append({
                "class_id": 0,
                "confidence": confidence,
                "bbox": [x, y, w, h],
                "source": "model"  # Add source for visual distinction
            })
        
        return predictions
