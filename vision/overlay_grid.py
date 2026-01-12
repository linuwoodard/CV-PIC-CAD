"""
Grid overlay utility for vision pipeline.
Draws a 10x10 grid with labeled rows (A-J) and columns (1-10) on images.
"""

import cv2
import numpy as np
from pathlib import Path


def overlay_grid_on_image(input_path: str, output_path: str = None) -> np.ndarray:
    """
    Load an image and overlay a 10x10 grid with labeled margins.
    
    Args:
        input_path: Path to input image
        output_path: Path to save output image (default: debug_grid_overlay.jpg in same directory)
    
    Returns:
        Image array with grid overlay
    """
    # Load the image
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Could not load image from {input_path}")
    
    # Get image dimensions
    h, w = img.shape[:2]
    
    # Create a copy to draw on
    img_with_grid = img.copy()
    
    # Calculate grid spacing
    # Leave margins for labels (top/bottom for rows, left/right for columns)
    margin_top = 60  # Space for row labels (A-J)
    margin_bottom = 40
    margin_left = 60  # Space for column labels (1-10)
    margin_right = 40
    
    grid_width = w - margin_left - margin_right
    grid_height = h - margin_top - margin_bottom
    
    # Calculate spacing for 10x10 grid (9 intervals = 10 cells)
    x_spacing = grid_width / 10
    y_spacing = grid_height / 10
    
    # Draw vertical lines (columns)
    for i in range(11):  # 0 to 10 (11 lines for 10 cells)
        x = int(margin_left + i * x_spacing)
        cv2.line(img_with_grid, (x, margin_top), (x, h - margin_bottom), (0, 0, 255), 2)
    
    # Draw horizontal lines (rows)
    for i in range(11):  # 0 to 10 (11 lines for 10 cells)
        y = int(margin_top + i * y_spacing)
        cv2.line(img_with_grid, (margin_left, y), (w - margin_right, y), (0, 0, 255), 2)
    
    # Font settings for large, distinct text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2
    font_thickness = 3
    text_color = (255, 0, 0)  # Blue (BGR format)
    
    # Label columns (1-10) at the top
    for i in range(10):
        col_num = str(i + 1)
        x = int(margin_left + (i + 0.5) * x_spacing)
        y = 40  # Position in top margin
        
        # Get text size for centering
        (text_w, text_h), baseline = cv2.getTextSize(col_num, font, font_scale, font_thickness)
        x_text = x - text_w // 2
        
        cv2.putText(img_with_grid, col_num, (x_text, y), font, font_scale, text_color, font_thickness)
    
    # Label columns (1-10) at the bottom
    for i in range(10):
        col_num = str(i + 1)
        x = int(margin_left + (i + 0.5) * x_spacing)
        y = h - 10  # Position in bottom margin
        
        # Get text size for centering
        (text_w, text_h), baseline = cv2.getTextSize(col_num, font, font_scale, font_thickness)
        x_text = x - text_w // 2
        
        cv2.putText(img_with_grid, col_num, (x_text, y), font, font_scale, text_color, font_thickness)
    
    # Label rows (A-J) on the left
    row_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    for i in range(10):
        row_label = row_labels[i]
        x = 20  # Position in left margin
        y = int(margin_top + (i + 0.5) * y_spacing)
        
        # Get text size for centering
        (text_w, text_h), baseline = cv2.getTextSize(row_label, font, font_scale, font_thickness)
        y_text = y + text_h // 2
        
        cv2.putText(img_with_grid, row_label, (x, y_text), font, font_scale, text_color, font_thickness)
    
    # Label rows (A-J) on the right
    for i in range(10):
        row_label = row_labels[i]
        x = w - 50  # Position in right margin
        y = int(margin_top + (i + 0.5) * y_spacing)
        
        # Get text size for centering
        (text_w, text_h), baseline = cv2.getTextSize(row_label, font, font_scale, font_thickness)
        y_text = y + text_h // 2
        
        cv2.putText(img_with_grid, row_label, (x, y_text), font, font_scale, text_color, font_thickness)
    
    # Determine output path
    if output_path is None:
        input_path_obj = Path(input_path)
        output_path = str(input_path_obj.parent / "debug_grid_overlay.jpg")
    
    # Save the result
    cv2.imwrite(output_path, img_with_grid)
    print(f"Grid overlay saved to: {output_path}")
    
    return img_with_grid


if __name__ == "__main__":
    # Test on a dummy image named test.jpg
    test_image_path = Path(__file__).parent / "input_images" / "GDS CV-2.jpg"
    output_path = Path(__file__).parent / "debug_output" / "GDS CV-2_grid_overlay.jpg"
    
    # Create a dummy test image if it doesn't exist
    if not test_image_path.exists():
        print(f"Creating dummy test image at {test_image_path}")
        # Create a simple test image (800x600 white image)
        dummy_img = np.ones((600, 800, 3), dtype=np.uint8) * 255
        cv2.imwrite(str(test_image_path), dummy_img)
    
    # Test the function
    try:
        result = overlay_grid_on_image(str(test_image_path), str(output_path))
        print("Grid overlay test completed successfully!")
        print(f"Result image shape: {result.shape}")
    except Exception as e:
        print(f"Error during test: {e}")
