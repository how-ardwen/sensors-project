### Using normal python project for now. Will be converted to notebook later ###

# Import libraries
import pygame
import random
import cv2
import os
import numpy as np

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

import ModelTraining
from tensorflow.keras.models import load_model

# Initialize Pygame
def init_pygame():

    pygame.init()
    screen = pygame.display.set_mode((1450, 800))
    pygame.display.set_caption("CameraGUI")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    return screen, clock, font

# Check for Pygame close event
def check_pygame_close_event():

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Quitting program.")
            return False
    return True

# Create directory for saving images
def create_image_directory():

    if not os.path.exists("CameraToClassification\Images\Saved_Images/"):
        os.makedirs("CameraToClassification\Images\Saved_Images/")
    if not os.path.exists("CameraToClassification\Images\Test_Images/"):
        os.makedirs("CameraToClassification\Images\Test_Images/")

# Launch camera
def launch_camera():

    camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    camera.set(cv2.CAP_PROP_FPS, 60)
    if not camera.isOpened():
        print("Error: Could not open camera.")
        exit()
    return camera

# Read image from camera
def read_camera_image(camera):

    ret, frame = camera.read()
    if not ret:
        print("Error: Failed to grab frame.")
        return None
    frame = translate_camera_frame(frame)
    return frame

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

# Save camera image to file
def save_camera_image(frame):

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rotated_frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    cv2.imwrite("CameraToClassification\Images\Test_Images\TestImage.jpg", rotated_frame)
    print(f"TestImage.jpg saved.")

    filename = os.path.splitext(os.path.basename(test_image))[0]
        
    print(f"Processing image: {filename}")
    
    img = Image.open(test_image)
    
    img = img.convert("RGB")
    img_width, img_height = img.size
    
    results = yolo_model(test_image)
    
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
        return
    
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
    
    # Apply mask to create final combined result
    hand_array = np.array(chosen_hand)
    hand_bgr = cv2.cvtColor(hand_array, cv2.COLOR_RGB2BGR)
    
    # Resize mask to match image dimensions if needed
    if bw_mask.shape[:2] != hand_bgr.shape[:2]:
        bw_mask = cv2.resize(bw_mask, (hand_bgr.shape[1], hand_bgr.shape[0]))
    
    # Apply mask: bitwise_and keeps color only where mask is white (255)
    masked_img = cv2.bitwise_and(hand_bgr, hand_bgr, mask=bw_mask)
    
    print(f"Completed processing {filename}")

     # Read image
    image = masked_img
    target_size = 700
    
    if image is None:
        print(f"Failed to read")
        return
    
    # Process original image
    processed_original = add_black_borders_to_square(image, target_size)
    cv2.imwrite("CameraToClassification\Images\Test_Images_Processed\TestImage_Combined_Border.png", processed_original)
    
    
    print(f"Processed image with black borders saved.")

    predicted_class, confidence = ModelTraining.predict_image(keras_model, image_path="CameraToClassification\Images\Test_Images_Processed\TestImage_Combined_Border.png")

    return predicted_class, confidence

# Map file counter to label
def file_counter_to_label(file_counter):

    if file_counter % 3 == 0:
        return "rock"
    elif file_counter % 3 == 1:
        return "paper"
    else:
        return "scissors"

# Translate camera frame for Pygame display
def translate_camera_frame(camera_frame):

    camera_frame = cv2.flip(camera_frame, 1)
    camera_frame = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
    return camera_frame

# Convert camera frame to Pygame surface
def frame_to_surface(camera_frame):

    camera_frame = cv2.transpose(camera_frame)
    frame_surface = pygame.surfarray.make_surface(camera_frame)
    return frame_surface

# Get center of the Pygame screen
def get_screen_center(screen):

    screen_rect = screen.get_rect()
    center_x = screen_rect.width // 2
    center_y = screen_rect.height // 2
    return (center_x, center_y)

# Get center of the camera frame
def get_camera_frame_center(camera_frame):

    frame_height, frame_width = camera_frame.shape[:2]
    center_x = frame_width // 2
    center_y = frame_height // 2
    return (center_x, center_y)

# Draw camera frame shape bounds on screen
def draw_frame_shape_bounds(camera_frame, offset):

    frame_height, frame_width = camera_frame.shape[:2]
    top_left = offset
    pygame.draw.rect(pygame.display.get_surface(), (0, 0, 255), (top_left[0], top_left[1], frame_width, frame_height), 2)

# Debug function to draw bounds and centers
def debug_draw_bounds(screen, camera_frame, camera_screen_offset):
    draw_frame_shape_bounds(camera_frame, camera_screen_offset)
    pygame.draw.circle(screen, (255, 0, 0), get_screen_center(screen), 5)
    pygame.draw.circle(screen, (0, 255, 0), camera_screen_offset, 5)

# Calculate offset to center camera frame on screen
def calculate_camera_screen_offset(screen, camera_frame):

    screen_center = get_screen_center(screen)
    frame_center = get_camera_frame_center(camera_frame)
    offset_x = screen_center[0] - frame_center[0]
    offset_y = screen_center[1] - frame_center[1]
    return (offset_x, offset_y)

# Generate random 5-digit session ID
def generate_random_5_digit_number():

    return str(random.randint(100000, 999999))

# Convert grid index to pixel position
def index_to_position(index_x, index_y, frame_width, frame_height):

    pos_x = index_x * frame_width
    pos_y = index_y * frame_height
    return (pos_x, pos_y)

# Main script
if __name__ == "__main__":

    yolo_model = YOLO("hand_yolov8s.pt")

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

    test_image = "CameraToClassification\Images\Test_Images\TestImage.jpg"

    keras_model = load_model(r"CameraToClassification\Models\final_trained_model_V1.h5")
    predicted_class = ""
    confidence = 0.0

    # Initialize variables
    camera = launch_camera()
    screen, clock, font = init_pygame()
    running = True
    camera_screen_offset = (0, 0)

    hand_type = 0
    file_counter = 0
    save_image = False
    sb_press_previous_frame = False

    # Create image file directory
    create_image_directory()

    # Generate session ID
    session_id = generate_random_5_digit_number()
    print(f"Session ID: {session_id}")

    # Main Loop
    while running:

        # Check for quit event
        running = check_pygame_close_event()

        save_image = False

        # keyboard input handling
        keys = pygame.key.get_pressed()

        if keys[pygame.K_SPACE]:
            if not sb_press_previous_frame:
                save_image = True
            sb_press_previous_frame = True
        else:
            sb_press_previous_frame = False

        # Read camera frame
        camera_frame = read_camera_image(camera)
        if camera_frame is None:
            print("No frame captured, exiting.")
            break

        # Clear screen to black
        screen.fill((0, 0, 0), (0, 0, screen.get_width(), screen.get_height()))

        # Normal display
        frame_surface = frame_to_surface(camera_frame)
        screen.blit(frame_surface, index_to_position(0, 0, camera_frame.shape[1], camera_frame.shape[0]))

        if save_image:
            predicted_class, confidence = save_camera_image(camera_frame)
            file_counter += 1

        # debug_draw_bounds(screen, camera_frame, (0,0))

        session_id_text = font.render("Session ID: " + session_id, True, (255, 255, 255))
        screen.blit(session_id_text, (10, 50))

        current_label = file_counter_to_label(hand_type)
        label_text = font.render("Current Label: " + current_label, True, (255, 255, 255))
        screen.blit(label_text, (10, 90))

        file_counter_text = font.render("Images Saved: " + str(file_counter), True, (255, 255, 255))
        screen.blit(file_counter_text, (10, 130))

        # Load and display the processed test image
        try:
            test_img = pygame.image.load("CameraToClassification\Images\Test_Images_Processed\TestImage_Combined_Border.png")
            test_img = pygame.transform.scale(test_img, (200, 200))
            screen.blit(test_img, (10, 210))
        except:
            pass

        test_image_text = font.render("Predicted Class: " + predicted_class + f" ({confidence:.2f})", True, (255, 255, 255))
        screen.blit(test_image_text, (10, 170))


        
        pygame.display.flip()
        clock.tick(30)

    camera.release()
    pygame.quit()

    ### END OF CODE ###