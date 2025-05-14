# XLabel
Computer Vision image labels are metadata. So lets treat them accordingly.

As an experiment, I'm exploring the idea of embedding computer vision annotation data directly into an image's EXIF tags, rather than storing it in separate sidecar text files. This approach effectively bundles the labels with the image itself, simplifying the dataset's file structure. While it's a bit unconventional, it could offer unexpected advantages — especially for smaller or proprietary datasets, or for fine-tuning tasks where managing separate annotation files adds unnecessary overhead. 

## Code

Embedding annotation data into EXIF tags can be a convenient way to store metadata directly within the image file. This approach can simplify data management, especially when working with large datasets. However, it's essential to consider the limitations and potential drawbacks:

+ EXIF tags have size limitations, which may restrict the amount of data that can be stored. 
+ Not all image formats support EXIF tags (e.g., PNG, GIF). 
+ Some image processing tools or libraries might strip or modify EXIF tags, potentially leading to data loss. 
    
The provided code is just a starting point, but it can be improved for better error handling, flexibility, and readability.

```python

import os
import json
import pyexiftool

def write_to_exif_tag(file_path, data, tag="UserComment"):
    """
    Write data to a specified EXIF tag of an image file.

    Args:
        file_path (str): Full path to the image file.
        data (str or dict): Data to store (dict is JSON-serialized).
        tag (str): EXIF tag to write to (default: UserComment).

    Returns:
        bool: True if successful, False otherwise.
    """
    if not os.path.isfile(file_path):
        print(f"Error: File {file_path} does not exist or is not a file.")
        return False

    # Convert dict to JSON string if necessary
    if isinstance(data, dict):
        try:
            data = json.dumps(data, ensure_ascii=False)
        except TypeError as e:
            print(f"Error serializing data to JSON: {e}")
            return False

    try:
        with pyexiftool.ExifTool() as et:
            et.write_metadata(file_path, {tag: data})
        return True
    except Exception as e:
        print(f"Error writing to EXIF tag {tag}: {e}")
        return False

def read_from_exif_tag(file_path, tag="UserComment", as_json=False):
    """
    Read data from a specified EXIF tag of an image file.

    Args:
        file_path (str): Full path to the image file.
        tag (str): EXIF tag to read from (default: UserComment).
        as_json (bool): If True, attempt to parse data as JSON (default: False).

    Returns:
        str or dict: Data stored in the EXIF tag, or None if not found.
    """
    if not os.path.isfile(file_path):
        print(f"Error: File {file_path} does not exist or is not a file.")
        return None

    try:
        with pyexiftool.ExifTool() as et:
            metadata = et.get_metadata(file_path)
            data = metadata.get(tag)
            if data and as_json:
                try:
                    return json.loads(data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from {tag}: {e}")
                    return None
            return data
    except Exception as e:
        print(f"Error reading from EXIF tag {tag}: {e}")
        return None

# Example usage
file_path = os.path.join("path", "to", "image", "image.jpg")
annotation = {
    "labels": ["cat", "dog"],
    "bbox": [100, 150, 200, 250]
}

# Write structured annotation data
success = write_to_exif_tag(file_path, annotation)
if success:
    print("Write successful")

# Read structured annotation data
data = read_from_exif_tag(file_path, as_json=True)
print(data)
```
## To do: Semi-Automatic Labeling Pipeline

To integrate this approach into a semi-automatic labeling pipeline, the following steps are suggested:

+ Data Preparation:
  Develop a script to extract the EXIF data from the images and store it in a temporary format (e.g., JSON, CSV) for easier processing. 
+ Labeling Tool:
  Create a simple labeling tool that allows users to review the images and update the annotation data stored in the EXIF tags. This tool can be a web application, desktop application, or even a Jupyter Notebook.
+ Data Validation:
  Implement data validation checks to ensure that the annotation data is in the correct format and within the size limits of the EXIF tags. 
+ Data Storage:
  Design a data storage system that can efficiently store and retrieve the annotated images, along with their corresponding EXIF data. 
+ Pipeline Automation:
  Automate the pipeline by integrating the data preparation, labeling, and storage steps using scripts or workflows (e.g., Apache Airflow, GitHub Actions).
    
## Tools and libraries for building a semi-automatic labeling pipeline include:

+ Labelbox: A platform for data annotation and labeling. 
+ Hasty.ai: A platform for data annotation and active learning. 
+ OpenCV: A computer vision library for image processing and analysis. 
+ PyTorch: A deep learning library for building and training machine learning models. 

