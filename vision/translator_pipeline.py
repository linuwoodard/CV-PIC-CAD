"""
Main translator pipeline for converting hand-drawn circuit schematics to GDS.
This script orchestrates the vision processing workflow.
"""

import cv2
import sys
from pathlib import Path

from overlay_grid import overlay_grid_on_image
from grid_tools import GridMapper


def send_to_vision_model(image_path: str):
    """
    Placeholder function for sending image to OpenAI/Gemini vision API.
    
    Args:
        image_path: Path to the grid-tagged image
    
    Returns:
        None (placeholder)
    """
    pass


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
    
    # Placeholder: send to vision model
    print("Sending to vision model...")
    send_to_vision_model(str(output_image_path))
    
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
