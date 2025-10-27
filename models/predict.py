import os, json, argparse

# Lazy imports - only import when needed to avoid numpy issues
_model = None
_device = None
_transform = None
_classes = None

def load_dependencies():
    """Lazy load all ML dependencies when first needed"""
    global _model, _device, _transform, _classes, torch, torch_nn, transforms, EfficientNet, cv2, np
    
    if _model is not None:
        return  # Already loaded
    
    # Import numpy FIRST to ensure it's available
    import numpy as np
    # Make sure numpy array operations work
    np.array([1, 2, 3])  # Test numpy
    
    # Now import torch and torchvision
    import torch
    import torch.nn as torch_nn
    from torchvision import transforms
    from efficientnet_pytorch import EfficientNet
    import cv2
    
    # Config - use absolute paths relative to this script's location
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    MODEL_PATH = os.path.join(SCRIPT_DIR, "efficientnet_b0_bat_3_dataset(1).pth")
    CLASSES_PATH = os.path.join(SCRIPT_DIR, "new_3_dataset_classes(1).json")
    
    # Load classes
    with open(CLASSES_PATH, 'r', encoding='utf-8') as f:
        _classes = json.load(f)
    
    # Device & transforms
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    
    # Load model
    def load_model(model_path, num_classes):
        model = EfficientNet.from_pretrained('efficientnet-b0')
        model._fc = torch_nn.Linear(model._fc.in_features, num_classes)
        try:
            model.load_state_dict(torch.load(model_path, map_location=_device, weights_only=True))
        except:
            model.load_state_dict(torch.load(model_path, map_location=_device, weights_only=False))
        model.eval().to(_device)
        return model
    
    _model = load_model(MODEL_PATH, len(_classes))

def classify_image(img_path):
    """
    Classify an image and return the predicted class and confidence.
    If confidence is below the threshold, return 'Unknown species'.
    """
    # Lazy load dependencies on first call
    load_dependencies()
    
    # Confidence threshold
    CONFIDENCE_THRESHOLD = 75.0
    
    # Use cv2 to load image (more compatible with numpy than PIL)
    img_cv = cv2.imread(img_path)
    if img_cv is None:
        raise ValueError(f"Failed to load image: {img_path}")
    
    # Convert BGR to RGB (cv2 loads in BGR by default)
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL for torchvision transforms
    from PIL import Image as PILImage
    img_pil = PILImage.fromarray(img_rgb)
    
    # Apply transforms
    x = _transform(img_pil).unsqueeze(0).to(_device)
   
    # Get prediction
    with torch.no_grad():
        output = _model(x)
        probs = torch.softmax(output, dim=1)[0]
        confidence, idx = probs.max(0)
        confidence_percent = round(confidence.item() * 100, 2)
        predicted_class = _classes[idx]
    
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
    