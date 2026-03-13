from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont, ExifTags
import numpy as np
import requests
import sys
import os
import cv2
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
import torch
import matplotlib.pyplot as plt
import glob

model = YOLO("hand_yolov8s.pt")

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

print("Python executable:", sys.executable)
print("Python version:", sys.version)

if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"using device: {device}")

if device.type == "cuda":
    # use bfloat16 for the entire notebook
    torch.autocast("cuda", dtype=torch.bfloat16).__enter__()
    # turn on tfloat32 for Ampere GPUs (https://pytorch.org/docs/stable/notes/cuda.html#tensorfloat-32-tf32-on-ampere-devices)
    if torch.cuda.get_device_properties(0).major >= 8:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
elif device.type == "mps":
    print(
        "\nSupport for MPS devices is preliminary. SAM 2 is trained with CUDA and might "
        "give numerically different outputs and sometimes degraded performance on MPS. "
        "See e.g. https://github.com/pytorch/pytorch/issues/84936 for a discussion."
    )

sam2_checkpoint = "C:/JupyterNotebookScripts/3350RockPaperScissors/AISE3350_RockPaperScissorsMinusOne/sam2.1_hiera_large.pt" # ALEX
model_cfg = "C:/JupyterNotebookScripts/3350RockPaperScissors/AISE3350_RockPaperScissorsMinusOne/sam2.1_hiera_l.yaml" # ALEX

sam2_model = build_sam2(model_cfg, sam2_checkpoint, device="cpu")

predictor = SAM2ImagePredictor(sam2_model)

# Get all images from the directory
image_dir = "CameraToClassification\\Images\\Saved_Images\\"
image_files = glob.glob(os.path.join(image_dir, "*.jpg")) + glob.glob(os.path.join(image_dir, "*.png"))

print(f"Found {len(image_files)} images to process")

counter = 0

# Loop through each image
for image in image_files:

    # Check if image has already been processed
    filename = os.path.splitext(os.path.basename(image))[0]
    combined_folder = "CameraToClassification\\Images\\Processed_Images\\Combined"
    expected_output = os.path.join(combined_folder, f"{filename}_Normal.png")

    if os.path.exists(expected_output):
        print(f"Image {filename} already processed, skipping and deleting original image...")
        os.remove(image)
        counter += 1
        continue

    counter += 1
    filename = os.path.splitext(os.path.basename(image))[0]
    
    print(f"Processing image: {filename}")
    
    img = Image.open(image)
    
    img = img.convert("RGB")
    img_width, img_height = img.size
    
    results = model(image)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    hand_list = [] 
    
    for i, box in enumerate(results[0].boxes):
        coords = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = coords
    
        cropped_hand = img.crop((x1, y1, x2, y2))
    
        hand_list.append(cropped_hand)
    
    # Find the largest hand by area
    max_area = 0
    chosen_hand = None
    
    for hand in hand_list:
        width, height = hand.size
        area = width * height
        if area > max_area:
            max_area = area
            chosen_hand = hand

    
    
    print(f"Chosen hand dimensions: {chosen_hand.size if chosen_hand else 'None'}, Area: {max_area}")
    
    if chosen_hand is None:
        print(f"No hands detected in {filename}, skipping...")
        continue
    
    bw_hand = 0
    
    image_array = np.array(chosen_hand.convert("RGB"))
    
    predictor.set_image(image_array)
    
    masks, scores, logits = predictor.predict(
        point_coords=None,
        point_labels=None,
        box=None,
        multimask_output=True
    )
    sorted_ind = np.argsort(scores)[::-1]
    masks = masks[sorted_ind]      # first mask
    
    first_mask = masks[0]          # shape (H, W)
    mask_bool = first_mask.astype(bool)
    
    bw_mask = (mask_bool * 255).astype(np.uint8)
    
    
    image_folder = "CameraToClassification\\Images\\Processed_Images\\Normal"
    mask_folder = "CameraToClassification\\Images\\Processed_Images\\Masks"
    
    
    os.makedirs(mask_folder, exist_ok=True)
    os.makedirs(image_folder, exist_ok=True)
    
    
    # Save hand images
    hand_array = np.array(chosen_hand)
    cv2.imwrite(f"CameraToClassification\\Images\\Processed_Images\\Normal\\{filename}_Normal.png", cv2.cvtColor(hand_array, cv2.COLOR_RGB2BGR))
    
    
    # Save mask images
    cv2.imwrite(f"CameraToClassification\\Images\\Processed_Images\\Masks\\{filename}_Mask_bw.png", bw_mask)
        
    output_folder = "CameraToClassification\\Images\\Processed_Images\\Combined"
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all image files sorted by number
    image_files_current = glob.glob(os.path.join(image_folder, f"{filename}_Normal.png"))
    mask_files = glob.glob(os.path.join(mask_folder, f"{filename}_Mask_bw.png"))
    
    masked_images = []
    
    for img_path, mask_path in zip(image_files_current, mask_files):
        # Read color image
        color_img = cv2.imread(img_path)
        
        # Read mask (grayscale)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        
        # Resize mask to match image dimensions if needed
        if mask.shape[:2] != color_img.shape[:2]:
            mask = cv2.resize(mask, (color_img.shape[1], color_img.shape[0]))
        
        # Apply mask: bitwise_and keeps color only where mask is white (255)
        masked_img = cv2.bitwise_and(color_img, color_img, mask=mask)
        
        masked_images.append(masked_img)
        
        # Save the result
        output_filename = os.path.basename(img_path).replace("hand_", "masked_hand_")
        cv2.imwrite(os.path.join(output_folder, output_filename), masked_img)

    # Delete original image file from Saved_Images directory
    if os.path.exists(image):
        os.remove(image)
        print(f"Deleted original image: {image}")
    
    print(f"Completed processing {filename}")
    print(f"Processed {counter/len(image_files)*100:.2f}% of images")
    # process this many our of total images
    print("Processed {}/{} images".format(counter, len(image_files)))

print(f"Finished processing all images")