from .predictor import ModelPredictor

import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages the state of the ML model, its settings, and predictions.
    """
    def __init__(self):
        self.available_models = {
            "YOLOv8n (General)": "models/yolov8n.pt",
            "Custom Model (Example)": "models/custom.pt"
        }
        self.selected_model_name = list(self.available_models.keys())[0]
        
        # --- Tweakable Parameters ---
        self.confidence_threshold = 0.45
        self.iou_threshold = 0.50
        # ---------------------------

        self._predictor = None
        self.load_model()

    def load_model(self, model_name: str = None):
        """Loads the specified model into the predictor."""
        if model_name:
            self.selected_model_name = model_name
        
        model_path = self.available_models[self.selected_model_name]
        logger.info(f"Loading model: {self.selected_model_name} from {model_path}")
        self._predictor = ModelPredictor(model_path)

    def set_confidence_threshold(self, value: float):
        """Sets the confidence threshold (0.0 to 1.0)."""
        self.confidence_threshold = max(0.0, min(1.0, value))
        logger.info(f"Confidence threshold set to: {self.confidence_threshold}")

    def set_iou_threshold(self, value: float):
        """Sets the IOU threshold for NMS (0.0 to 1.0)."""
        self.iou_threshold = max(0.0, min(1.0, value))
        logger.info(f"IOU threshold set to: {self.iou_threshold}")

    def predict(self, image_path: str, image_width: int, image_height: int) -> list:
        """Runs prediction using the currently loaded model and settings."""
        if not self._predictor:
            logger.error("Predictor not loaded.")
            return []
        
        try:
            return self._predictor.predict(
                image_path=image_path,
                image_width=image_width,
                image_height=image_height,
                confidence_threshold=self.confidence_threshold,
                iou_threshold=self.iou_threshold
            )
        except NotImplementedError as e:
            logger.warning(f"{e}")
            return []
