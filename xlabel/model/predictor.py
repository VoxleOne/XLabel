import random

class ModelPredictor:
    """
    A class to handle model inference for semi-automated annotation.
    This is a mock implementation and should be replaced with a real model loader
    (e.g., Ultralytics YOLO, Detectron2).
    """
    def __init__(self, model_path: str):
        """
        Initializes the model predictor.

        Args:
            model_path (str): The path to the trained model file.
                              (Currently unused in this mock implementation).
        """
        self.model_path = model_path
        # --- REAL IMPLEMENTATION ---
        # from ultralytics import YOLO
        # try:
        #     self.model = YOLO(model_path)
        # except Exception as e:
        #     print(f"Error loading model: {e}")
        #     self.model = None
        print(f"ModelPredictor initialized for model: {model_path}")

    def predict(self, image_path: str, image_width: int, image_height: int) -> list:
        """
        Runs inference on a given image and returns predictions.

        Args:
            image_path (str): Path to the image file.
            image_width (int): The width of the image.
            image_height (int): The height of the image.

        Returns:
            list: A list of prediction dictionaries. Each dictionary should contain
                  at least a 'bbox' key with [x, y, w, h].
        """
        print(f"Running mock prediction on: {image_path}")
        # --- REAL IMPLEMENTATION ---
        # if not self.model:
        #     return []
        # results = self.model(image_path)
        # predictions = []
        # for r in results:
        #     for box in r.boxes:
        #         cls_id = int(box.cls[0])
        #         confidence = float(box.conf[0])
        #         x1, y1, x2, y2 = map(int, box.xyxy[0])
        #         predictions.append({
        #             "class_id": cls_id,
        #             "confidence": confidence,
        #             "bbox": [x1, y1, x2 - x1, y2 - y1] # Convert to x, y, w, h
        #         })
        # return predictions

        # --- MOCK IMPLEMENTATION ---
        # For demonstration, generate a few random bounding boxes.
        predictions = []
        for i in range(random.randint(3, 8)):
            w = random.randint(int(image_width * 0.1), int(image_width * 0.3))
            h = random.randint(int(image_height * 0.1), int(image_height * 0.3))
            x = random.randint(0, image_width - w)
            y = random.randint(0, image_height - h)
            predictions.append({
                "class_id": 0,
                "confidence": round(random.uniform(0.75, 0.98), 2),
                "bbox": [x, y, w, h]
            })
        
        return predictions
