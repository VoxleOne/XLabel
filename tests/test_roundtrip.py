"""Round-trip tests: creator.add_xlabel_metadata_to_png → reader.read_xlabel_metadata_from_png."""

import copy
import os

import pytest

from xlabel import creator, reader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_and_read(dummy_png, tmp_dir, metadata):
    """Helper: embed metadata into a copy of the dummy PNG, then read it back."""
    out = os.path.join(tmp_dir, "output.png")
    creator.add_xlabel_metadata_to_png(dummy_png, out, copy.deepcopy(metadata), overwrite=True)
    return reader.read_xlabel_metadata_from_png(out)


# ---------------------------------------------------------------------------
# Basic round-trip
# ---------------------------------------------------------------------------

class TestRoundtripBasic:
    def test_basic_bbox(self, dummy_png, tmp_dir, basic_metadata):
        result = _write_and_read(dummy_png, tmp_dir, basic_metadata)
        assert result is not None
        assert result["xlabel_version"] == creator.XLABEL_VERSION
        assert result["class_names"] == ["cat", "dog"]
        assert len(result["annotations"]) == 1
        ann = result["annotations"][0]
        assert ann["class_id"] == 0
        assert ann["bbox"] == [10, 20, 100, 80]
        assert ann["score"] == pytest.approx(0.95, abs=1e-5)
        assert ann["custom_attributes"] == {"color": "orange"}

    def test_empty_annotations(self, dummy_png, tmp_dir):
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["a"],
            "annotations": [],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result is not None
        assert result["annotations"] == []

    def test_many_classes(self, dummy_png, tmp_dir):
        names = [f"class_{i}" for i in range(100)]
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": names,
            "annotations": [
                {"class_id": i, "bbox": [0, 0, 10, 10], "custom_attributes": {}}
                for i in range(100)
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result["class_names"] == names
        assert len(result["annotations"]) == 100


# ---------------------------------------------------------------------------
# Segmentation round-trips
# ---------------------------------------------------------------------------

class TestRoundtripSegmentation:
    def test_polygon_segmentation(self, dummy_png, tmp_dir):
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["shape"],
            "annotations": [
                {
                    "class_id": 0,
                    "bbox": [20, 20, 70, 80],
                    "score": 0.90,
                    "segmentation": [[20, 20, 90, 20, 90, 100, 20, 100]],
                    "custom_attributes": {},
                },
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        ann = result["annotations"][0]
        assert ann["segmentation"] == [[20, 20, 90, 20, 90, 100, 20, 100]]

    def test_rle_segmentation(self, dummy_png, tmp_dir):
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["mask"],
            "annotations": [
                {
                    "class_id": 0,
                    "bbox": [80, 80, 60, 70],
                    "score": 0.88,
                    "segmentation": {
                        "rle_size": [240, 320],
                        "rle_counts": [100, 5, 200, 10, 5000],
                    },
                    "custom_attributes": {},
                },
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        seg = result["annotations"][0]["segmentation"]
        assert isinstance(seg, dict)
        assert seg["rle_size"] == [240, 320]
        assert seg["rle_counts"] == [100, 5, 200, 10, 5000]

    def test_multiple_mixed_annotations(self, dummy_png, tmp_dir):
        """10 annotations mixing bbox-only, polygon, and RLE."""
        annotations = []
        for i in range(10):
            ann = {
                "class_id": i % 3,
                "bbox": [i * 10, i * 5, 50, 40],
                "score": round(0.5 + i * 0.04, 2),
                "custom_attributes": {"idx": i},
            }
            if i % 3 == 1:
                ann["segmentation"] = [[0, 0, 10, 0, 10, 10, 0, 10]]
            elif i % 3 == 2:
                ann["segmentation"] = {
                    "rle_size": [240, 320],
                    "rle_counts": [1, 2, 3],
                }
            annotations.append(ann)

        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["a", "b", "c"],
            "annotations": annotations,
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert len(result["annotations"]) == 10
        for i, ann in enumerate(result["annotations"]):
            assert ann["class_id"] == i % 3
            assert ann["bbox"] == [i * 10, i * 5, 50, 40]
            assert ann["custom_attributes"] == {"idx": i}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestRoundtripEdgeCases:
    def test_unicode_class_names(self, dummy_png, tmp_dir):
        names = ["猫", "犬", "café", "naïve"]
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": names,
            "annotations": [
                {"class_id": 0, "bbox": [0, 0, 10, 10], "custom_attributes": {}}
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result["class_names"] == names

    def test_max_length_class_name(self, dummy_png, tmp_dir):
        # 255 bytes is the max for a class name (uint8 length prefix)
        long_name = "a" * 255
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": [long_name],
            "annotations": [
                {"class_id": 0, "bbox": [0, 0, 10, 10], "custom_attributes": {}}
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result["class_names"] == [long_name]

    def test_score_zero(self, dummy_png, tmp_dir):
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["x"],
            "annotations": [
                {"class_id": 0, "bbox": [0, 0, 1, 1], "score": 0.0, "custom_attributes": {}}
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result["annotations"][0]["score"] == pytest.approx(0.0, abs=1e-5)

    def test_score_one(self, dummy_png, tmp_dir):
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["x"],
            "annotations": [
                {"class_id": 0, "bbox": [0, 0, 1, 1], "score": 1.0, "custom_attributes": {}}
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result["annotations"][0]["score"] == pytest.approx(1.0, abs=1e-5)

    def test_no_score_sentinel(self, dummy_png, tmp_dir):
        """When no score is provided, the creator writes -1.0 and the reader omits it."""
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["x"],
            "annotations": [
                {"class_id": 0, "bbox": [0, 0, 1, 1], "custom_attributes": {}}
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert "score" not in result["annotations"][0]

    def test_nested_custom_attributes(self, dummy_png, tmp_dir):
        attrs = {"level1": {"level2": [1, 2, {"deep": True}]}}
        meta = {
            "image_properties": {"filename": "dummy.png", "width": 320, "height": 240},
            "class_names": ["x"],
            "annotations": [
                {"class_id": 0, "bbox": [0, 0, 1, 1], "custom_attributes": attrs}
            ],
        }
        result = _write_and_read(dummy_png, tmp_dir, meta)
        assert result["annotations"][0]["custom_attributes"] == attrs


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

class TestErrorPaths:
    def test_read_non_xlabel_png(self, dummy_png):
        """A plain PNG with no xlDa chunk returns None."""
        result = reader.read_xlabel_metadata_from_png(dummy_png)
        assert result is None

    def test_read_non_png_file(self, tmp_dir):
        """A text file masquerading as PNG raises XLabelFormatError."""
        bad = os.path.join(tmp_dir, "fake.png")
        with open(bad, "w") as f:
            f.write("Not a PNG file")
        with pytest.raises(reader.XLabelFormatError):
            reader.read_xlabel_metadata_from_png(bad)

    def test_create_invalid_metadata(self, dummy_png, tmp_dir):
        """Missing required fields in metadata raises XLabelFormatError."""
        out = os.path.join(tmp_dir, "out.png")
        with pytest.raises(creator.XLabelFormatError):
            creator.add_xlabel_metadata_to_png(dummy_png, out, {"bad": "data"})

    def test_create_nonexistent_input(self, tmp_dir):
        """Non-existent input image raises FileNotFoundError."""
        out = os.path.join(tmp_dir, "out.png")
        meta = {
            "image_properties": {"filename": "x.png", "width": 1, "height": 1},
            "class_names": [],
            "annotations": [],
        }
        with pytest.raises(FileNotFoundError):
            creator.add_xlabel_metadata_to_png("/nonexistent.png", out, meta)
