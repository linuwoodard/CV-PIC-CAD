"""
Main translator pipeline for converting hand-drawn circuit schematics to GDS.
This script orchestrates the vision processing workflow.
"""

import base64
import cv2
import os
import re
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

from overlay_grid import overlay_grid_on_image
from grid_tools import GridMapper
from prompts import GRID_SYSTEM_PROMPT_V3
from reference_library import EXAMPLES


def construct_prompt_with_examples(base_prompt: str) -> str:
    """
    Construct a system prompt by appending few-shot examples from the reference library.
    
    Args:
        base_prompt: The base system prompt to enhance with examples
    
    Returns:
        Enhanced prompt string with examples appended
    """
    prompt = base_prompt
    
    # Append examples section
    prompt += "\n\n### FEW-SHOT REFERENCE EXAMPLES\n"
    prompt += "Study these examples carefully. They demonstrate the correct format and handling of common patterns:\n\n"
    
    for i, example in enumerate(EXAMPLES, start=1):
        prompt += f"--- Example {i}: {example['name']} ---\n"
        prompt += f"Description: {example['description']}\n\n"
        prompt += "Expected YAML output:\n"
        prompt += example['yaml']
        prompt += "\n\n"
    
    return prompt


def send_to_vision_model(image_path: str, system_prompt: str = GRID_SYSTEM_PROMPT_V3):
    """
    Send image to Gemini 1.5 Pro vision API.
    
    Args:
        image_path: Path to the grid-tagged image
        system_prompt: Optional system prompt (default: GRID_SYSTEM_PROMPT from prompts.py)
    
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
        from google.genai import Client
    except ImportError:
        raise ImportError("google-genai library not installed. Run: pip install google-genai")
    
    # Get API key from environment variable
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    try:
        # Initialize client with API key using context manager for proper cleanup
        with Client(api_key=api_key) as client:
            # Build prompt (Gemini doesn't have separate system/user roles, so combine them)
            full_prompt = user_prompt
            if system_prompt:
                full_prompt = system_prompt
            
            # Prepare content - decode base64 and create PIL Image
            import PIL.Image
            import io
            
            image_data = base64.b64decode(base64_image)
            image = PIL.Image.open(io.BytesIO(image_data))
            
            # Make API call with image and prompt
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[full_prompt, image]
            )
            
            # Return raw response text
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            return response.text
        
    except Exception as e:
        raise ConnectionError(f"API connection error: {str(e)}")


def parse_ai_response(response_text: str, mapper: GridMapper, output_path: Path = None, image_name: str = None, save_file: bool = True):
    """
    Post-process AI response: strip markdown, parse YAML, convert grid references to integers.
    
    Args:
        response_text: Raw string response from the AI (may contain markdown fencing)
        mapper: GridMapper instance for converting grid references to pixel coordinates
        output_path: Path to save the final YAML file (default: output/circuit_<image_name>.yaml)
        image_name: Name of the input image (without extension) to include in filename
        save_file: Whether to save the YAML file to disk (default: True)
    
    Returns:
        Dictionary containing the parsed and processed circuit data
    
    Raises:
        ValueError: If YAML parsing fails or placements section is missing
    """
    # Strip markdown fencing (like ```yaml or ```)
    # Remove any markdown code blocks
    text = response_text.strip()
    
    # Pattern to match markdown code fences (```yaml, ```yml, ```, etc.)
    markdown_pattern = r'^```(?:yaml|yml)?\s*\n(.*?)\n```\s*$'
    match = re.search(markdown_pattern, text, re.DOTALL | re.MULTILINE)
    if match:
        text = match.group(1)
    else:
        # Try to remove just the opening/closing fences if they exist separately
        text = re.sub(r'^```(?:yaml|yml)?\s*\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    
    # Parse the string into a Python dictionary using yaml.safe_load
    try:
        circuit_dict = yaml.safe_load(text)
        if circuit_dict is None:
            raise ValueError("YAML parsing resulted in None - check if response contains valid YAML")
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML: {e}")
    
    # Check if placements section exists
    if 'placements' not in circuit_dict:
        raise ValueError("YAML does not contain a 'placements' section")
    
    # Loop through the placements section
    placements = circuit_dict['placements']
    for instance_name, placement_data in placements.items():
        if not isinstance(placement_data, dict):
            continue
        
        # Skip conversion for relative placement keys (to, port, dx, dy)
        # These should remain as strings/numbers and not be converted
        if 'to' in placement_data or 'port' in placement_data:
            # This is a relative placement - skip grid conversion
            # dx and dy should already be numbers, but ensure they're not strings
            if 'dx' in placement_data and isinstance(placement_data['dx'], str):
                try:
                    placement_data['dx'] = float(placement_data['dx'])
                except ValueError:
                    print(f"Warning: Could not convert dx='{placement_data['dx']}' for instance '{instance_name}'")
            if 'dy' in placement_data and isinstance(placement_data['dy'], str):
                try:
                    placement_data['dy'] = float(placement_data['dy'])
                except ValueError:
                    print(f"Warning: Could not convert dy='{placement_data['dy']}' for instance '{instance_name}'")
            continue  # Skip grid conversion for relative placements
        
        # Only convert x/y for absolute placements (anchor component)
        # Check x value
        if 'x' in placement_data:
            x_value = placement_data['x']
            # If x is a string like 'C3', convert it to integer using GridMapper
            if isinstance(x_value, str):
                try:
                    x_pixel, _ = mapper.get_center_of_cell(x_value)
                    placement_data['x'] = x_pixel
                except ValueError:
                    # If conversion fails, keep the original value
                    print(f"Warning: Could not convert x='{x_value}' for instance '{instance_name}', keeping original value")
        
        # Check y value
        if 'y' in placement_data:
            y_value = placement_data['y']
            # If y is a string like 'C3', convert it to integer using GridMapper
            if isinstance(y_value, str):
                try:
                    _, y_pixel = mapper.get_center_of_cell(y_value)
                    placement_data['y'] = y_pixel
                except ValueError:
                    # If conversion fails, keep the original value
                    print(f"Warning: Could not convert y='{y_value}' for instance '{instance_name}', keeping original value")
    
    # Save file only if save_file is True
    if save_file:
        # Set default output path if not provided
        if output_path is None:
            if image_name:
                filename = f"circuit_{image_name}.yaml"
            else:
                filename = "circuit.yaml"
            output_path = Path(__file__).parent.parent / "output" / filename
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the final dictionary to output/circuit.yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(circuit_dict, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"Processed circuit data saved to: {output_path}")
    
    return circuit_dict


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
        # Construct enhanced prompt with few-shot examples
        enhanced_prompt = construct_prompt_with_examples(GRID_SYSTEM_PROMPT_V3)
        response = send_to_vision_model(str(output_image_path), system_prompt=enhanced_prompt)
        print("\nVision model response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        # Save response to file
        response_path = output_dir / f"{input_path.stem}_ai_response.txt"
        with open(response_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"\nResponse saved to: {response_path}")
        
        # Parse and process the AI response
        print("\nParsing AI response...")
        try:
            circuit_dict = parse_ai_response(response, mapper, image_name=input_path.stem)
            print("Successfully parsed and processed circuit data.")
        except ValueError as e:
            print(f"Warning: Failed to parse AI response: {e}")
            print("Raw response saved, but YAML processing skipped.")
        
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
