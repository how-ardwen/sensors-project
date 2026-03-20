### Using normal python project for now. Will be converted to notebook later ###

# Import libraries
import pygame
import random
import time
import cv2
import os
import numpy as np

from PIL import Image
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

# Launch camera
def launch_camera():

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920/3)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080/3)
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

# Save camera image to file
def save_camera_image(frame):

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    cv2.imwrite("CameraToClassification\Images\Test_Images/TestImage.jpg", frame)
    print(f"Saved image")

    output_size = (1000, 1000)
    input_directory = "CameraToClassification\Images\Test_Images/"
    output_directory = "CameraToClassification\Images\Test_Images_Processed/"
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
        square_img = Image.new('RGB', (max_dim, max_dim), 'black')
        
        # Paste original image in center
        paste_x = (max_dim - width) // 2
        paste_y = (max_dim - height) // 2
        square_img.paste(img, (paste_x, paste_y))
        
        # Resize to target size
        resized_img = square_img.resize(output_size, Image.Resampling.LANCZOS)
        
        # Save processed image
        output_path = os.path.join(output_directory, f"processed_{image_file}")
        resized_img.save(output_path)
        
    print(f"Processed {len(image_files)} images to {output_size[0]}x{output_size[1]}")

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

# Apply nonlinear brightness adjustment with additional clipping threshold
def apply_nonlinear_brightness(gray, threshold=128, dark_power=1.8, bright_power=0.6, clip_threshold=0):
    a = gray.astype(np.float32) / 255.0
    t = threshold / 255.0
    out = np.empty_like(a)
    mask = a < t
    # dim values -> get dimmer
    out[mask] = t * (a[mask] / t) ** dark_power
    # bright values -> get brighter
    out[~mask] = t + (1 - t) * ((a[~mask] - t) / (1 - t)) ** bright_power
    out = np.clip(out * 255.0, 0, 255).astype('uint8')
    if clip_threshold > 0:
        out[out < clip_threshold] = 0
    return out

# Tick function
def tick(interval_ms, last_execution_time, current_time, frame, model, predicted_class, confidence):
    if current_time - last_execution_time >= interval_ms:
        predicted_class, confidence = ModelTraining.predict_image(model)
        save_camera_image(frame)
        return current_time, predicted_class, confidence
    return last_execution_time, predicted_class, confidence

# Main script
if __name__ == "__main__":

    # Initialize variables
    camera = launch_camera()
    screen, clock, font = init_pygame()
    running = True
    camera_screen_offset = (0, 0)

    file_counter = 0
    save_image = False
    sb_press_previous_frame = False

    threshold = 180
    dark_power = 20
    bright_power = 1
    clip_threshold = 30

    last_frame_time = 0

    model = load_model("CameraToClassification\Models/trained_model_masked_colour.h5")
    predicted_class = ""
    confidence = 0.0

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
        # Adjust threshold
        if keys[pygame.K_KP4]:
            threshold = min(255, threshold + 1)
        if keys[pygame.K_KP1]: # DOWN arrow
            threshold = max(0, threshold - 1)
        # Adjust dark power
        if keys[pygame.K_KP5]:
            dark_power = min(40.0, dark_power + 0.5)
        if keys[pygame.K_KP2]:
            dark_power = max(0.01, dark_power - 0.5)
        # Adjust bright power
        if keys[pygame.K_KP6]:
            bright_power = min(5.0, bright_power + 0.01)
        if keys[pygame.K_KP3]:
            bright_power = max(0.01, bright_power - 0.01)
        # Adjust clip threshold
        if keys[pygame.K_KP0]:
            clip_threshold = min(255, clip_threshold + 1)
        if keys[pygame.K_KP_PERIOD]:
            clip_threshold = max(0, clip_threshold - 1)
        # Save image on spacebar press
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
        screen.fill((200, 200, 200), (0, 0, screen.get_width(), screen.get_height()))

        # Normal display
        frame_surface = frame_to_surface(camera_frame)
        screen.blit(frame_surface, index_to_position(0, 0, camera_frame.shape[1], camera_frame.shape[0]))

        # RED channel display
        red_channel = camera_frame.copy()
        red_channel[:, :, [1,2]] = 0
        # red_frame_surface = frame_to_surface(red_channel)
        # screen.blit(red_frame_surface, index_to_position(1, 0, camera_frame.shape[1], camera_frame.shape[0]))

        red_gray = cv2.cvtColor(red_channel, cv2.COLOR_RGB2GRAY)
        red_gray = cv2.normalize(red_gray, None, 0, 255, cv2.NORM_MINMAX).astype('uint8')
        red_gray_rgb = cv2.cvtColor(red_gray, cv2.COLOR_GRAY2RGB)
        # red_gray_surface = frame_to_surface(red_gray_rgb)
        # screen.blit(red_gray_surface, index_to_position(1, 1, camera_frame.shape[1], camera_frame.shape[0]))

        red_gray_nl = apply_nonlinear_brightness(red_gray, threshold, dark_power, bright_power, clip_threshold)
        red_gray_rgb_nl = cv2.cvtColor(red_gray_nl, cv2.COLOR_GRAY2RGB)
        red_gray_surface_nl = frame_to_surface(red_gray_rgb_nl)
        screen.blit(red_gray_surface_nl, index_to_position(1, 0, camera_frame.shape[1], camera_frame.shape[0]))

        # GREEN channel display
        # green_channel = camera_frame.copy()
        # green_channel[:, :, [0,2]] = 0
        # green_frame_surface = frame_to_surface(green_channel)
        # screen.blit(green_frame_surface, index_to_position(2, 0, camera_frame.shape[1], camera_frame.shape[0]))

        # green_gray = cv2.cvtColor(green_channel, cv2.COLOR_RGB2GRAY)
        # green_gray = cv2.normalize(green_gray, None, 0, 255, cv2.NORM_MINMAX).astype('uint8')
        # green_gray_rgb = cv2.cvtColor(green_gray, cv2.COLOR_GRAY2RGB)
        # green_gray_surface = frame_to_surface(green_gray_rgb)
        # screen.blit(green_gray_surface, index_to_position(2, 1, camera_frame.shape[1], camera_frame.shape[0]))

        # green_gray_nl = apply_nonlinear_brightness(green_gray, threshold, dark_power, bright_power)
        # green_gray_rgb_nl = cv2.cvtColor(green_gray_nl, cv2.COLOR_GRAY2RGB)
        # green_gray_surface_nl = frame_to_surface(green_gray_rgb_nl)
        # screen.blit(green_gray_surface_nl, index_to_position(2, 2, camera_frame.shape[1], camera_frame.shape[0]))

        # # BLUE channel display
        # blue_channel = camera_frame.copy()
        # blue_channel[:, :, [0,1]] = 0
        # blue_frame_surface = frame_to_surface(blue_channel)
        # screen.blit(blue_frame_surface, index_to_position(3, 0, camera_frame.shape[1], camera_frame.shape[0]))

        # blue_gray = cv2.cvtColor(blue_channel, cv2.COLOR_RGB2GRAY)
        # blue_gray = cv2.normalize(blue_gray, None, 0, 255, cv2.NORM_MINMAX).astype('uint8')
        # blue_gray_rgb = cv2.cvtColor(blue_gray, cv2.COLOR_GRAY2RGB)
        # blue_gray_surface = frame_to_surface(blue_gray_rgb)
        # screen.blit(blue_gray_surface, index_to_position(3, 1, camera_frame.shape[1], camera_frame.shape[0]))

        # blue_gray_nl = apply_nonlinear_brightness(blue_gray, threshold, dark_power, bright_power)
        # blue_gray_rgb_nl = cv2.cvtColor(blue_gray_nl, cv2.COLOR_GRAY2RGB)
        # blue_gray_surface_nl = frame_to_surface(blue_gray_rgb_nl)
        # screen.blit(blue_gray_surface_nl, index_to_position(3, 2, camera_frame.shape[1], camera_frame.shape[0]))

        masked_frame = cv2.bitwise_and(camera_frame, red_gray_rgb_nl)
        masked_frame_surface = frame_to_surface(masked_frame)
        screen.blit(masked_frame_surface, index_to_position(1, 1, camera_frame.shape[1], camera_frame.shape[0]))

        current_time = time.time_ns() // 1_000_000  # Convert nanoseconds to milliseconds
        last_frame_time, predicted_class, confidence = tick(100, last_frame_time, current_time, masked_frame, model, predicted_class, confidence)
        print(f"Frame time: {last_frame_time} ms")

        # debug_draw_bounds(screen, camera_frame, (0,0))

        session_id_text = font.render("Session ID: " + session_id, True, (255, 255, 255))
        screen.blit(session_id_text, (10, 50))

        current_label = file_counter_to_label(file_counter)
        label_text = font.render("Current Label: " + current_label, True, (255, 255, 255))
        screen.blit(label_text, (10, 90))

        threshold_text = font.render(f"Threshold: {threshold}", True, (255, 255, 255))
        screen.blit(threshold_text, (10, 130))

        dark_power_text = font.render(f"Dark Power: {dark_power}", True, (255, 255, 255))
        screen.blit(dark_power_text, (10, 170))

        bright_power_text = font.render(f"Bright Power: {bright_power}", True, (255, 255, 255))
        screen.blit(bright_power_text, (10, 210))

        clip_threshold_text = font.render(f"Clip Threshold: {clip_threshold}", True, (255, 255, 255))
        screen.blit(clip_threshold_text, (10, 250))

        font2 = pygame.font.SysFont(None, 60)
        prediction_text = font2.render(f"Prediction: {predicted_class} ({confidence:.2f})", True, (0, 0, 0))
        screen.blit(prediction_text, (10, 500))
        
        pygame.display.flip()
        clock.tick(30)

    camera.release()
    pygame.quit()

    ### END OF CODE ###