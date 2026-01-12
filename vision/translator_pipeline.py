"""
Main translator pipeline for converting hand-drawn circuit schematics to GDS.
This script orchestrates the vision processing workflow.
"""

import base64
import cv2
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

from overlay_grid import overlay_grid_on_image
from grid_tools import GridMapper


def send_to_vision_model(image_path: str, system_prompt: str = None):
    """
    Send image to Gemini 1.5 Pro vision API.
    
    Args:
        image_path: Path to the grid-tagged image
        system_prompt: Optional system prompt (default: None)
    
    Returns:
        Raw string response from the vision model
    
    Raises:
        FileNotFoundError: If image_path doesn't exist
        ValueError: If API key is not set or other validation errors
        ConnectionError: If API connection fails
    """
    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Encode image to base64
    with open(image_path_obj, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    # User prompt as specified
    user_prompt = "Analyze this image. Identify the optical components and their approximate grid locations."
    
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai library not installed. Run: pip install google-generativeai")
    
    # Get API key from environment variable
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    try:
        genai.configure(api_key=api_key)
        
        # Create model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Build prompt (Gemini doesn't have separate system/user roles, so combine them)
        full_prompt = user_prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Prepare content - decode base64 and create PIL Image
        import PIL.Image
        import io
        
        image_data = base64.b64decode(base64_image)
        image = PIL.Image.open(io.BytesIO(image_data))
        
        # Make API call
        response = model.generate_content([full_prompt, image])
        
        # Return raw response text
        if not response.text:
            raise ValueError("Empty response from Gemini API")
        return response.text
        
    except Exception as e:
        raise ConnectionError(f"API connection error: {str(e)}")


def main(input_image_path: str = None, output_dir: Path = None):
    """
    Main pipeline workflow.
    
    Args:
        input_image_path: Path to input image (default: looks for images in input_images/)
        output_dir: Directory to save output (default: debug_output/)
    """
    # Set default paths
    if input_image_path is None:
        # Look for images in input_images directory
        input_dir = Path(__file__).parent / "input_images"
        image_files = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png"))
        if not image_files:
            raise FileNotFoundError(f"No images found in {input_dir}")
        input_image_path = str(image_files[0])
        print(f"Using first available image: {input_image_path}")
    
    input_path = Path(input_image_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_image_path}")
    
    # Set output directory
    if output_dir is None:
        output_dir = Path(__file__).parent / "debug_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load image to get dimensions
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Could not load image from {input_path}")
    
    height, width = img.shape[:2]
    print(f"Loaded image: {input_path.name} ({width}x{height} pixels)")
    
    # Instantiate GridMapper
    mapper = GridMapper(image_width=width, image_height=height, rows=10, cols=10)
    
    # Create output path for grid overlay
    output_image_path = output_dir / f"{input_path.stem}_grid_overlay.jpg"
    
    # Call overlay_grid_on_image to create the tagged image
    print("Overlaying grid on image...")
    tagged_image = overlay_grid_on_image(str(input_path), str(output_image_path))
    
    # Get pixel coordinates for grid cell A1
    x, y = mapper.get_center_of_cell('A1')
    
    # Print console log
    print(f"Prepared image for AI. Grid Cell A1 corresponds to pixel ({x}, {y})")
    
    # Send to vision model
    print("Sending to vision model...")
    try:
        response = send_to_vision_model(str(output_image_path))
        print("\nVision model response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        # Save response to file
        response_path = output_dir / f"{input_path.stem}_ai_response.txt"
        with open(response_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"\nResponse saved to: {response_path}")
        
    except (ConnectionError, ValueError, ImportError, FileNotFoundError) as e:
        print(f"Warning: Vision model API call failed: {e}")
        print("Continuing without AI analysis...")
        response = None
    
    print("Pipeline completed successfully!")
    return str(output_image_path)


if __name__ == "__main__":
    # Allow command-line argument for image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = None
    
    try:
        result_path = main(image_path)
        print(f"\nOutput saved to: {result_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
