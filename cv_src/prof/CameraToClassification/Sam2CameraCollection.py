### Using normal python project for now. Will be converted to notebook later ###

# Import libraries
import pygame
import random
import cv2
import os
import numpy as np

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

# Save camera image to file
def save_camera_image(frame, file_counter, hand_type, session_id):

    label = file_counter_to_label(hand_type)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rotated_frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    cv2.imwrite("CameraToClassification\Images\Saved_Images/" + label + "_" + session_id + "_" + str(file_counter) + ".jpg", rotated_frame)
    print(f"Saved image: {label}_{session_id}_{file_counter}.jpg")

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
        if keys[pygame.K_r]:
            hand_type = 0
        if keys[pygame.K_p]:
            hand_type = 1
        if keys[pygame.K_s]:
            hand_type = 2

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
            save_camera_image(camera_frame, file_counter, hand_type, session_id)
            file_counter += 1

        # debug_draw_bounds(screen, camera_frame, (0,0))

        session_id_text = font.render("Session ID: " + session_id, True, (255, 255, 255))
        screen.blit(session_id_text, (10, 50))

        current_label = file_counter_to_label(hand_type)
        label_text = font.render("Current Label: " + current_label, True, (255, 255, 255))
        screen.blit(label_text, (10, 90))

        file_counter_text = font.render("Images Saved: " + str(file_counter), True, (255, 255, 255))
        screen.blit(file_counter_text, (10, 130))
        
        pygame.display.flip()
        clock.tick(30)

    camera.release()
    pygame.quit()

    ### END OF CODE ###