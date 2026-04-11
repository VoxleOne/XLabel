import logging

logger = logging.getLogger(__name__)


class ModelPredictor:
    """
    A class to handle model inference for semi-automated annotation.

    This is a stub implementation. To enable real predictions, install a
    compatible model backend (e.g., ``pip install ultralytics``) and replace
    this class with a real model loader.
    """
    def __init__(self, model_path: str):
        self.model_path = model_path
        logger.warning(
            "ModelPredictor is a stub. No real model is loaded. "
            "Replace this with a real model backend to enable predictions."
        )

    def predict(self, image_path: str, image_width: int, image_height: int, 
                confidence_threshold: float, iou_threshold: float) -> list:
        """
        Runs inference on a given image and returns predictions based on thresholds.

        Raises NotImplementedError because no real model backend is configured.
        """
        raise NotImplementedError(
            "Model inference is not yet implemented. "
            "To enable predictions, install a compatible model backend "
            "(e.g., 'pip install ultralytics') and replace this stub "
            "with a real model loader in xlabel/model/predictor.py."
        )
