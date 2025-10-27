import os, json, torch, argparse
import numpy as np
from PIL import Image
import torch.nn as nn  
from torchvision import transforms
from efficientnet_pytorch import EfficientNet

# Config - use absolute paths relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "efficientnet_b0_bat_3_dataset(1).pth")
CLASSES_PATH = os.path.join(SCRIPT_DIR, "new_3_dataset_classes(1).json")

# Confidence threshold - predictions below this will be marked as unknown
CONFIDENCE_THRESHOLD = 75.0

# Device & transforms
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# Load classes
with open(CLASSES_PATH, 'r', encoding='utf-8') as f:
    classes = json.load(f)

# Load model
def load_model(model_path, num_classes):
    model = EfficientNet.from_pretrained('efficientnet-b0')
    model._fc = nn.Linear(model._fc.in_features, num_classes)
    try:
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    except:
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=False))
    model.eval().to(device)
    return model

# Preload model
model = load_model(MODEL_PATH, len(classes))

def classify_image(img_path):
    """
    Classify an image and return the predicted class and confidence.
    If confidence is below the threshold, return 'Unknown species'.
    """
    img = Image.open(img_path).convert("RGB")
    x = transform(img).unsqueeze(0).to(device)
   
    # Get prediction
    with torch.no_grad():
        output = model(x)
        probs = torch.softmax(output, dim=1)[0]
        confidence, idx = probs.max(0)
        confidence_percent = round(confidence.item() * 100, 2)
        predicted_class = classes[idx]
    
    # Check confidence threshold
    if confidence_percent < CONFIDENCE_THRESHOLD:
        final_prediction = "Unknown species"
        print(f"Low confidence prediction: {predicted_class} ({confidence_percent}%) -> Returning: {final_prediction}")
    else:
        final_prediction = predicted_class
        print(f"High confidence prediction: {predicted_class} ({confidence_percent}%)")
    
    return final_prediction, confidence_percent

# --- CLI Execution Block ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Classify a bat spectrogram image using EfficientNet.")
    parser.add_argument('image_path', type=str, help='Path to the spectrogram image file (e.g., spectrogram.jpg)')
    
    args = parser.parse_args()
    
    prediction, confidence = classify_image(args.image_path)
    
    print("\n--- Final Result ---")
    print(f"Predicted Species: {prediction}")
    print(f"Confidence: {confidence}%")
    