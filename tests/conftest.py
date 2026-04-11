import os
import tempfile

import pytest
from PIL import Image


@pytest.fixture
def tmp_dir():
    """Provides a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def dummy_png(tmp_dir):
    """Creates a dummy 320x240 RGB PNG and returns its path."""
    path = os.path.join(tmp_dir, "dummy.png")
    Image.new("RGB", (320, 240), color="blue").save(path)
    return path


@pytest.fixture
def basic_metadata():
    """Returns a minimal valid v0.2.0 metadata dict with one bbox annotation."""
    return {
        "image_properties": {
            "filename": "dummy.png",
            "width": 320,
            "height": 240,
        },
        "class_names": ["cat", "dog"],
        "annotations": [
            {
                "class_id": 0,
                "bbox": [10, 20, 100, 80],
                "score": 0.95,
                "custom_attributes": {"color": "orange"},
            },
        ],
    }
