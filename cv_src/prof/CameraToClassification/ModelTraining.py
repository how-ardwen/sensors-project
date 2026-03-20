import os
import numpy as np
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Flatten, Dropout
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
import glob

def train_and_save_model(data_dir, model_save_path):
    # Lists to store images and labels
    images = []
    labels = []
    label_mapping = {'rock': 0, 'paper': 1, 'scissors': 2}
    
    # Load and preprocess images
    image_paths = glob.glob(os.path.join(data_dir, "*.png")) + glob.glob(os.path.join(data_dir, "*.jpg"))  # Include both PNG and JPG
    for image_path in image_paths:
        # Extract label from filename (assumes format: label_*)
        filename = os.path.basename(image_path)
        label = None
        if filename.startswith('rock_'):
            label = 'rock'
        elif filename.startswith('paper_'):
            label = 'paper'
        elif filename.startswith('scissors_'):
            label = 'scissors'
        
        if label is None:
            print(f"Warning: Skipping file with no valid label: {image_path}")
            continue
        
        # Load and preprocess image
        img = load_img(image_path, color_mode='rgb', target_size=(700, 700))
        img_array = img_to_array(img)
        img_array = img_array / 255.0  # Normalize pixel values
        
        images.append(img_array)
        labels.append(label_mapping[label])
    
    # Convert to numpy arrays
    X = np.array(images)
    y = np.array(labels)
    
    # # Define the model
    # model = Sequential([
    #     Conv2D(32, (3, 3), activation='relu', input_shape=(200, 200, 3)),
    #     MaxPooling2D(2, 2),
    #     Conv2D(64, (3, 3), activation='relu'),
    #     MaxPooling2D(2, 2),
    #     Conv2D(64, (3, 3), activation='relu'),
    #     MaxPooling2D(2, 2),
    #     Flatten(),
    #     Dense(64, activation='relu'),
    #     Dropout(0.5),
    #     Dense(3, activation='softmax')
    # ])

    # Define the model
    model = Sequential([
        # First block
        Conv2D(32, (3, 3), activation='relu', padding='same', input_shape=(700, 700, 3)),
        Conv2D(32, (3, 3), activation='relu', padding='same'),
        MaxPooling2D(2, 2),
        Dropout(0.25),
        
        # Second block
        Conv2D(64, (3, 3), activation='relu', padding='same'),
        Conv2D(64, (3, 3), activation='relu', padding='same'),
        MaxPooling2D(2, 2),
        Dropout(0.25),
        
        # Third block
        Conv2D(128, (3, 3), activation='relu', padding='same'),
        Conv2D(128, (3, 3), activation='relu', padding='same'),
        MaxPooling2D(2, 2),
        Dropout(0.25),
        
        # Fourth block
        Conv2D(256, (3, 3), activation='relu', padding='same'),
        Conv2D(256, (3, 3), activation='relu', padding='same'),
        MaxPooling2D(2, 2),
        Dropout(0.25),
        
        # Dense layers
        Flatten(),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(256, activation='relu'),
        Dropout(0.5),
        Dense(3, activation='softmax')
    ])
    
    # # Compile the model
    # model.compile(optimizer='adam',
    #              loss='sparse_categorical_crossentropy',
    #              metrics=['accuracy'])
    
    # Compile the model with optimized settings
    model.compile(
        optimizer=Adam(learning_rate=0.0001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    # Define callbacks for better training
    callbacks = [
        # Stop training when validation loss stops improving
        EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        # Reduce learning rate when validation loss plateaus
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-7,
            verbose=1
        ),
        # Save the best model during training
        ModelCheckpoint(
            filepath=model_save_path.replace('.h5', '_best.h5'),
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        )
    ]
    
    # # Train the model
    # history = model.fit(X, y, epochs=20, validation_split=0.2)

        # Train the model with optimized settings
    history = model.fit(
        X, y,
        epochs=100,
        batch_size=16,
        validation_split=0.2,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save the model
    model.save(model_save_path)
    
    return model, history

def predict_image(model, image_path=None):
    if image_path is None:
        image_path = r"CameraToClassification/Images/Test_Images_Processed/processed_TestImage.jpg"
    image_path = os.path.normpath(image_path)
    # Load and preprocess as RGB to match training
    img = load_img(image_path, color_mode='rgb', target_size=(700, 700))
    img_array = img_to_array(img).astype('float32') / 255.0
    img_array = np.expand_dims(img_array, axis=0)  # shape (1, 700, 700, 3)
    
    # Make prediction
    prediction = model.predict(img_array)
    class_names = ['rock', 'paper', 'scissors']
    predicted_class = class_names[np.argmax(prediction)]
    confidence = float(np.max(prediction))
    
    return predicted_class, confidence

# Example usage
if __name__ == "__main__":
    # Set paths
    # data_directory = "CameraToClassification\\Images\\Augmented_Images"
    # model_save_path = "CameraToClassification\\Models\\final_trained_model.h5"
    
    # Train and save model
    # model, history = train_and_save_model(data_directory, model_save_path)

    model_save_path = r"CameraToClassification\Models\final_trained_model.h5"
    
    # Load saved model (you can use this in a separate script)
    model = load_model(model_save_path)
    
    # Test the model with a single image
    test_image_path = r"CameraToClassification\Images\Test_Images_Processed\TestImage_Combined_Border.png"
    predicted_class, confidence = predict_image(model, test_image_path)
    print(f"Predicted class: {predicted_class}")
    print(f"Confidence: {confidence:.2f}")