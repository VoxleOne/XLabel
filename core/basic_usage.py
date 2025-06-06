import os
from xlabelcore import write_to_exif_tag, read_from_exif_tag

# Ensure you have an image file at this path for testing
# For example, create a dummy 'test_image.jpg' in an 'images' directory
# and place it in the same directory as this script or provide a full path.
# os.makedirs("images", exist_ok=True)
# open("images/image.jpg", "a").close() # Create a dummy file if it doesn't exist

file_path = os.path.join("images", "image.jpg") # Adjust path as needed

# Create a dummy file for testing if it doesn't exist
if not os.path.exists(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write("This is a dummy image file.") # exiftool might complain if not a valid image
    print(f"Created a dummy file for testing: {file_path}")
    print("Please replace it with a valid JPG image to test EXIF functionality.")


annotation = {
    "labels": ["cat", "dog"],
    "bbox": [100, 150, 200, 250],
    "source": "manual_annotation_v1"
}

print(f"Attempting to write annotation to {file_path}...")
# Write structured annotation data
# Using a more specific tag like 'XPComment' (Windows specific) or 'Description'
# UserComment is widely available.
success = write_to_exif_tag(file_path, annotation, tag="UserComment")
if success:
    print("Write successful")
else:
    print("Write failed")

print(f"\nAttempting to read annotation from {file_path}...")
# Read structured annotation data
data = read_from_exif_tag(file_path, tag="UserComment", as_json=True)

if data:
    print("Read data:")
    print(data)
    if isinstance(data, dict) and "labels" in data:
        print(f"Labels found: {data['labels']}")
else:
    print("Failed to read data or data not found.")

# Example: Reading a standard EXIF tag like 'Make' or 'Model'
# This might return None if the image has no such tag or if it's not a valid image
print("\nAttempting to read camera Make...")
camera_make = read_from_exif_tag(file_path, tag="Make")
if camera_make:
    print(f"Camera Make: {camera_make}")
else:
    print("Camera Make not found or error reading tag.")