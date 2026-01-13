"""
Optical Circuit Digitizer - Desktop GUI Application
Simple tkinter interface for the vision pipeline.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

import cv2
import yaml
from PIL import Image, ImageTk

# Import translator pipeline functions
import sys
sys.path.insert(0, str(Path(__file__).parent / "vision"))
from translator_pipeline import (
    send_to_vision_model,
    parse_ai_response,
    construct_prompt_with_examples
)
from prompts import GRID_SYSTEM_PROMPT_V3
from overlay_grid import overlay_grid_on_image
from grid_tools import GridMapper


class OpticalCircuitDigitizerGUI:
    """Main GUI application class."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Optical Circuit Digitizer")
        self.root.geometry("800x600")
        
        # Variable to store selected filename
        self.selected_filename = tk.StringVar(value="No file selected")
        self.current_file = None  # Store current file path
        
        # Create and layout widgets
        self._create_widgets()
        self._layout_widgets()
        
        # Set initial status
        self.update_status("Ready")
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Top Section: Frame for top controls
        top_frame = tk.Frame(self.root)
        
        self.select_button = tk.Button(
            top_frame,
            text="Select Image",
            command=self._on_select_image,
            width=15,
            height=2
        )
        
        self.filename_label = tk.Label(
            top_frame,
            textvariable=self.selected_filename,
            anchor="w",
            padx=10,
            font=("Arial", 10)
        )
        
        # Middle Section: PanedWindow for resizable split view
        self.middle_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        
        # Left side: ScrolledText for YAML
        yaml_frame = tk.Frame(self.middle_container)
        self.yaml_text = ScrolledText(
            yaml_frame,
            wrap=tk.WORD,
            width=40,
            height=25,
            font=("Courier", 10)
        )
        self.yaml_text.pack(fill=tk.BOTH, expand=True)
        
        # Right side: Image display label
        image_frame = tk.Frame(self.middle_container)
        self.image_display_label = tk.Label(
            image_frame,
            text="No image selected",
            width=50,
            height=25,
            bg="lightgray",
            relief=tk.SUNKEN,
            anchor="center"
        )
        self.image_display_label.pack(fill=tk.BOTH, expand=True)
        
        # Add frames to PanedWindow
        self.middle_container.add(yaml_frame, minsize=200)
        self.middle_container.add(image_frame, minsize=200)
        
        # Bottom Section: Frame for action buttons
        bottom_frame = tk.Frame(self.root)
        
        self.generate_button = tk.Button(
            bottom_frame,
            text="Generate CAD",
            command=self._on_generate_cad,
            width=15,
            height=2,
            bg="#4CAF50",  # Green color
            fg="white",
            font=("Arial", 10, "bold")
        )
        
        self.cancel_button = tk.Button(
            bottom_frame,
            text="Cancel / Clear",
            command=self._on_cancel_clear,
            width=15,
            height=2,
            bg="#f44336",  # Red color
            fg="white",
            font=("Arial", 10)
        )
        
        # Status Bar
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            anchor="w",
            relief=tk.SUNKEN,
            padx=5,
            pady=2,
            font=("Arial", 9)
        )
        
        # Store frames for layout
        self.top_frame = top_frame
        self.bottom_frame = bottom_frame
    
    def _layout_widgets(self):
        """Layout all widgets using pack."""
        # Top Section
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        self.select_button.pack(side=tk.LEFT, padx=(0, 10))
        self.filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Middle Section: Split view container (PanedWindow)
        self.middle_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Bottom Section: Buttons
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        self.generate_button.pack(side=tk.LEFT)
        self.cancel_button.pack(side=tk.RIGHT)
        
        # Status Bar (pack last so it stays at bottom)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _on_select_image(self):
        """Handle Select Image button click - triggers upload_action."""
        self.upload_action()
    
    def _on_generate_cad(self):
        """Handle Generate CAD button click - triggers submit_action."""
        self.submit_action()
    
    def _on_cancel_clear(self):
        """Handle Cancel / Clear button click - triggers cancel_action."""
        self.cancel_action()
    
    def upload_action(self):
        """Open file dialog, analyze image, and populate YAML text."""
        # Open file dialog for image selection
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )
        
        if not file_path:
            return  # User cancelled
        
        # Update filename label
        self.current_file = file_path
        filename = os.path.basename(file_path)
        self.selected_filename.set(filename)
        
        # A. Generate Grid Image immediately
        try:
            # Create output directory for grid overlay
            output_dir = Path(__file__).parent / "vision" / "debug_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create grid overlay
            input_path = Path(file_path)
            temp_grid_image_path = output_dir / f"{input_path.stem}_grid_overlay_temp.jpg"
            overlay_grid_on_image(str(file_path), str(temp_grid_image_path))
            
            # B. Open & Resize with PIL
            pil_image = Image.open(temp_grid_image_path)
            # Use LANCZOS resampling (works with both old and new PIL versions)
            try:
                pil_image.thumbnail((400, 400), Image.Resampling.LANCZOS)
            except AttributeError:
                # Fallback for older PIL versions
                pil_image.thumbnail((400, 400), Image.LANCZOS)
            
            # C. Convert to Tkinter Object
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # D. Display the image
            self.image_display_label.config(image=tk_image, text="")
            
            # IMPORTANT GC FIX: Keep reference to prevent garbage collection
            self.image_display_label.image = tk_image
            
        except Exception as e:
            self.update_status(f"Error creating grid overlay: {str(e)}")
            return
        
        # Update status
        self.update_status("Analyzing Image... (This may take a few seconds)")
        
        # Disable button during processing
        self.select_button.config(state="disabled")
        
        # E. Start Thread for vision API calls
        thread = threading.Thread(
            target=self._analyze_image_thread,
            args=(file_path, str(temp_grid_image_path)),
            daemon=True
        )
        thread.start()
    
    def _analyze_image_thread(self, image_path: str, grid_image_path: str):
        """Background thread to analyze image and get YAML."""
        try:
            # Load image to get dimensions
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            height, width = img.shape[:2]
            
            # Create GridMapper
            mapper = GridMapper(image_width=width, image_height=height, rows=10, cols=10)
            
            # Grid overlay already created in upload_action, use the provided path
            output_image_path = Path(grid_image_path)
            
            # Construct enhanced prompt with examples
            enhanced_prompt = construct_prompt_with_examples(GRID_SYSTEM_PROMPT_V3)
            
            # Send to vision model
            response = send_to_vision_model(str(output_image_path), system_prompt=enhanced_prompt)
            
            # Parse and convert grid references
            input_path = Path(image_path)
            circuit_dict = parse_ai_response(
                response,
                mapper,
                image_name=input_path.stem
            )
            
            # Convert dictionary to YAML string
            yaml_string = yaml.dump(
                circuit_dict,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
            
            # Update UI on main thread
            self.root.after(0, self._update_yaml_text, yaml_string, None)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            # Update UI on main thread with error
            self.root.after(0, self._update_yaml_text, None, error_msg)
    
    def _update_yaml_text(self, yaml_string: str = None, error_msg: str = None):
        """Update YAML text widget (called from main thread via root.after)."""
        # Re-enable button
        self.select_button.config(state="normal")
        
        if error_msg:
            self.update_status(f"Error: {error_msg}")
            self.yaml_text.delete("1.0", tk.END)
            self.yaml_text.insert("1.0", f"# Error occurred during analysis:\n{error_msg}")
        else:
            self.update_status("Analysis complete. Review and edit YAML if needed.")
            # Clear existing text and insert new YAML
            self.yaml_text.delete("1.0", tk.END)
            self.yaml_text.insert("1.0", yaml_string)
    
    def submit_action(self):
        """Get YAML text and save to output/circuit.yaml."""
        # Get text from ScrolledText widget
        yaml_content = self.yaml_text.get("1.0", tk.END)
        
        # Create output directory if it doesn't exist
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to output/circuit.yaml
        output_file = output_dir / "circuit.yaml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        
        # Update status
        self.update_status(f"Success: YAML saved to {output_file}")
        
        # Print confirmation
        print(f"YAML saved successfully to: {output_file}")
    
    def cancel_action(self):
        """Clear the text box and reset status."""
        # Clear text box
        self.yaml_text.delete("1.0", tk.END)
        
        # Clear image display
        self.image_display_label.config(image="", text="No image selected")
        self.image_display_label.image = None  # Clear reference
        
        # Reset status
        self.update_status("Ready")
        
        # Clear current file variable
        self.current_file = None
        self.selected_filename.set("No file selected")
    
    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.root.update_idletasks()


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = OpticalCircuitDigitizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
