import os
import cv2
import numpy as np
from pathlib import Path

def add_black_borders_to_square(image, target_size=700):
    """
    Add black borders to make image square without cropping.
    
    Args:
        image: Input image (numpy array)
        target_size: Target size for square image (default 700)
    
    Returns:
        Square image with black borders
    """
    height, width = image.shape[:2]
    
    # Calculate padding needed
    if height > width:
        pad_total = height - width
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        pad_top = 0
        pad_bottom = 0
    else:
        pad_total = width - height
        pad_top = pad_total // 2
        pad_bottom = pad_total - pad_top
        pad_left = 0
        pad_right = 0
    
    # Add black borders
    bordered_image = cv2.copyMakeBorder(
        image,
        pad_top, pad_bottom, pad_left, pad_right,
        cv2.BORDER_CONSTANT,
        value=[0, 0, 0]
    )
    
    # Resize to target size
    resized_image = cv2.resize(bordered_image, (target_size, target_size))
    
    return resized_image

def process_images(input_dir, output_dir, target_size=700):
    """
    Process all images: create mirrored versions and resize to square.
    
    Args:
        input_dir: Directory containing input images
        output_dir: Directory to save processed images
        target_size: Target square size (default 700)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all image files
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = [f for f in os.listdir(input_dir) 
                   if f.lower().endswith(image_extensions)]
    
    # Get existing files in output directory
    existing_files = set()
    if os.path.exists(output_dir):
        existing_files = set(os.listdir(output_dir))
    
    # Filter out images that are already processed
    images_to_process = []
    for image_file in image_files:
        name, ext = os.path.splitext(image_file)
        original_name = f"{name}{ext}"
        mirrored_name = f"{name}_mirrored{ext}"
        
        # Only process if both files don't exist
        if original_name not in existing_files or mirrored_name not in existing_files:
            images_to_process.append(image_file)
    
    image_files = images_to_process
    
    print(f"Found {len(image_files)} images to process")
    
    for image_file in image_files:
        input_path = os.path.join(input_dir, image_file)
        
        # Read image
        image = cv2.imread(input_path)
        
        if image is None:
            print(f"Failed to read: {image_file}")
            continue
        
        # Get filename without extension
        name, ext = os.path.splitext(image_file)
        
        # Process original image
        processed_original = add_black_borders_to_square(image, target_size)
        output_path_original = os.path.join(output_dir, f"{name}{ext}")
        cv2.imwrite(output_path_original, processed_original)
        
        # Process mirrored image
        mirrored_image = cv2.flip(image, 1)  # 1 for horizontal flip
        processed_mirrored = add_black_borders_to_square(mirrored_image, target_size)
        output_path_mirrored = os.path.join(output_dir, f"{name}_mirrored{ext}")
        cv2.imwrite(output_path_mirrored, processed_mirrored)
        
        print(f"Processed: {image_file} -> {name}{ext} and {name}_mirrored{ext}")
    
    print(f"\nProcessing complete! {len(image_files) * 2} images saved to {output_dir}")

if __name__ == "__main__":
    # Define paths
    input_directory = r"CameraToClassification\\Images\\Processed_Images\\Combined"
    output_directory = r"CameraToClassification\\Images\\Augmented_Images"
    
    # Process images
    process_images(input_directory, output_directory, target_size=700)