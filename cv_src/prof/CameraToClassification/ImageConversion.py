import os
from PIL import Image
import numpy as np
from PIL import ImageOps
import random

def process_images(input_directory="CameraToClassification\Images\Saved_Images/", padfillcolour="black", output_size=(1000, 1000)):
    # Create output directory if it doesn't exist
    output_directory = "CameraToClassification\Images\Processed_Images/"
    os.makedirs(output_directory, exist_ok=True)
    
    # Get list of image files
    image_files = [f for f in os.listdir(input_directory) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    for image_file in image_files:
        # Load image
        input_path = os.path.join(input_directory, image_file)
        img = Image.open(input_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Make image square with black padding
        width, height = img.size
        max_dim = max(width, height)
        square_img = Image.new('RGB', (max_dim, max_dim), padfillcolour)
        
        # Paste original image in center
        paste_x = (max_dim - width) // 2
        paste_y = (max_dim - height) // 2
        square_img.paste(img, (paste_x, paste_y))
        
        # Resize to target size
        resized_img = square_img.resize(output_size, Image.Resampling.LANCZOS)
        
        # Save processed image
        output_path = os.path.join(output_directory, f"processed_{image_file}")
        resized_img.save(output_path)
        
    return f"Processed {len(image_files)} images to {output_size[0]}x{output_size[1]}"

def augment_images(input_directory="CameraToClassification\Images\Processed_Images/", padfillcolour="black", output_size=(1000, 1000)):
    
    # Create output directory for augmented images
    augmented_directory = "CameraToClassification\Images\Augmented_Images/"
    os.makedirs(augmented_directory, exist_ok=True)
    
    # Get list of processed image files
    image_files = [f for f in os.listdir(input_directory) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    total_images = 0
    
    for image_file in image_files:
        # Load image
        input_path = os.path.join(input_directory, image_file)
        img = Image.open(input_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Process both original and mirrored versions
        versions = [
            ('original', img),
            ('mirrored', ImageOps.mirror(img))
        ]
        
        for version_name, base_img in versions:
            # Generate 3 zoom levels (always include 1.0)
            zoom_levels = [1.0]  # Original zoom
            while len(zoom_levels) < 3:
                zoom = round(random.uniform(0.8, 1.5), 2)
                if zoom not in zoom_levels:
                    zoom_levels.append(zoom)
            
            for zoom_idx, zoom in enumerate(zoom_levels):
                # Apply zoom
                if zoom != 1.0:
                    new_size = (int(output_size[0] * zoom), int(output_size[1] * zoom))
                    zoomed_img = base_img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Create canvas and center the zoomed image
                    canvas = Image.new('RGB', output_size, padfillcolour)
                    paste_x = (output_size[0] - new_size[0]) // 2
                    paste_y = (output_size[1] - new_size[1]) // 2
                    canvas.paste(zoomed_img, (paste_x, paste_y))
                    zoomed_img = canvas
                else:
                    zoomed_img = base_img.copy()
                
                # Generate 10 rotation angles (always include 0)
                angles = [0.0]  # Original angle
                while len(angles) < 10:
                    angle = round(random.uniform(-45, 45), 2)
                    if angle not in angles:
                        angles.append(angle)
                
                for angle_idx, angle in enumerate(angles):
                    # Apply rotation with white fill
                    if angle != 0:
                        rotated_img = zoomed_img.rotate(
                            angle,
                            resample=Image.Resampling.BICUBIC,
                            expand=False,
                            fillcolor=padfillcolour
                        )
                    else:
                        rotated_img = zoomed_img.copy()
                    
                    # Generate 10 random shifts
                    for shift_idx in range(10):
                        shift_x = random.randint(-100, 100)
                        shift_y = random.randint(-100, 100)
                        
                        # Apply shift
                        shifted_img = Image.new('RGB', output_size, padfillcolour)
                        shifted_img.paste(rotated_img, (shift_x, shift_y))
                        
                        # Create descriptive filename
                        base_name = os.path.splitext(image_file)[0]
                        aug_filename = f"{version_name}_zoom{zoom}_angle{angle}_shift{shift_x}_{shift_y}_{base_name}.jpg"
                        
                        # Save augmented image
                        output_path = os.path.join(augmented_directory, aug_filename)
                        shifted_img.save(output_path)
                        total_images += 1
    
    return f"Augmented {len(image_files)} images into {total_images} total images (2 versions × 3 zooms × 10 angles × 10 shifts per image)."

# def augment_images(input_directory="CameraToClassification\Images\Processed_Images/", padfillcolour="black",output_size=(1000, 1000)):
    
#     # Create output directory for augmented images
#     augmented_directory = "CameraToClassification\Images\Augmented_Images/"
#     os.makedirs(augmented_directory, exist_ok=True)
    
#     # Get list of processed image files
#     image_files = [f for f in os.listdir(input_directory) 
#                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
#     for image_file in image_files:
#         # Load image
#         input_path = os.path.join(input_directory, image_file)
#         img = Image.open(input_path)
        
#         # Step 1: Mirroring
#         mirrored_img = ImageOps.mirror(img)
#         mirrored_img.save(os.path.join(augmented_directory, f"mirrored_{image_file}"))
        
#         # Step 2: Rotations at 45/2 (22.5°) increments
#         step = 45.0 / 2.0  # 22.5 degrees
#         num_steps = int(360 / step)
#         angles = [round(step * i, 2) for i in range(1, num_steps)]  # 22.5, 45.0, 67.5, ..., 337.5

#         for angle in angles:
#             rotated_img = mirrored_img.rotate(angle)
#             # rotate with expansion and white fill so corners are white, not black
#             rotated_img = mirrored_img.rotate(
#                 angle,
#                 resample=Image.Resampling.BICUBIC,
#                 expand=True,
#                 fillcolor=padfillcolour
#             )
#             rotated_img.save(os.path.join(augmented_directory, f"rotated_{angle}_{image_file}"))
        
#         # Step 3: Slight shifts (translations) of the rotated images
#         shifts = [5, 10, 15]
#         for angle in angles:
#             rotated_path = os.path.join(augmented_directory, f"rotated_{angle}_{image_file}")
#             rotated_img = Image.open(rotated_path)
#             for shift in shifts:
#                 translated_img = Image.new('RGB', rotated_img.size, padfillcolour)
#                 translated_img.paste(rotated_img, (shift, 0))  # Horizontal shift
#                 translated_img.save(os.path.join(augmented_directory, f"shifted_{shift}_{angle}_{image_file}"))
                
#                 translated_img = Image.new('RGB', rotated_img.size, padfillcolour)
#                 translated_img.paste(rotated_img, (-shift, 0))  # Horizontal shift in the opposite direction
#                 translated_img.save(os.path.join(augmented_directory, f"shifted_{-shift}_{angle}_{image_file}"))
        
#     return f"Augmented {len(image_files)} images with various transformations."

def delete_files(directory_path):
    # Check if directory exists
    if not os.path.exists(directory_path):
        return f"Directory {directory_path} does not exist"
    
    # Get all files in directory
    files = os.listdir(directory_path)
    
    # Delete each file
    for file in files:
        file_path = os.path.join(directory_path, file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
    
    return f"Deleted {len(files)} files from {directory_path}"

# Run the processing
if __name__ == "__main__":

    fillcolour = "black"  # Black fill color for padding

    Aug = "CameraToClassification\Images\Augmented_Images/"
    Pro = "CameraToClassification\Images\Processed_Images/"
    Save = "CameraToClassification\Images\Saved_Images/"

    # print(process_images(), fillcolour)

    # print(augment_images())

    # delete_files(Save)
    # delete_files(Aug)
    # delete_files(Pro)

    print("Done!")