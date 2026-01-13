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
        # Top Section: Select Image button and filename label
        self.select_button = tk.Button(
            self.root,
            text="Select Image",
            command=self._on_select_image,
            width=15,
            height=2
        )
        
        self.filename_label = tk.Label(
            self.root,
            textvariable=self.selected_filename,
            anchor="w",
            padx=10,
            font=("Arial", 10)
        )
        
        # Middle Section: ScrolledText for YAML
        self.yaml_text = ScrolledText(
            self.root,
            wrap=tk.WORD,
            width=80,
            height=25,
            font=("Courier", 10)
        )
        
        # Bottom Section: Action buttons
        self.generate_button = tk.Button(
            self.root,
            text="Generate CAD",
            command=self._on_generate_cad,
            width=15,
            height=2,
            bg="#4CAF50",  # Green color
            fg="white",
            font=("Arial", 10, "bold")
        )
        
        self.cancel_button = tk.Button(
            self.root,
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
    
    def _layout_widgets(self):
        """Layout all widgets using grid."""
        # Top Section
        self.select_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.filename_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Configure grid column weights for resizing
        self.root.columnconfigure(1, weight=1)
        
        # Middle Section: YAML text area
        self.yaml_text.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        # Configure row weight for text area to expand
        self.root.rowconfigure(1, weight=1)
        
        # Bottom Section: Buttons
        self.generate_button.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.cancel_button.grid(row=2, column=1, padx=10, pady=10, sticky="e")
        
        # Status Bar
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
    
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
        
        # Update status
        self.update_status("Analyzing Image... (This may take a few seconds)")
        
        # Disable button during processing
        self.select_button.config(state="disabled")
        
        # Run analysis in a separate thread
        thread = threading.Thread(
            target=self._analyze_image_thread,
            args=(file_path,),
            daemon=True
        )
        thread.start()
    
    def _analyze_image_thread(self, image_path: str):
        """Background thread to analyze image and get YAML."""
        try:
            # Load image to get dimensions
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            height, width = img.shape[:2]
            
            # Create GridMapper
            mapper = GridMapper(image_width=width, image_height=height, rows=10, cols=10)
            
            # Create output directory for grid overlay
            output_dir = Path(__file__).parent / "vision" / "debug_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create grid overlay
            input_path = Path(image_path)
            output_image_path = output_dir / f"{input_path.stem}_grid_overlay.jpg"
            overlay_grid_on_image(str(image_path), str(output_image_path))
            
            # Construct enhanced prompt with examples
            enhanced_prompt = construct_prompt_with_examples(GRID_SYSTEM_PROMPT_V3)
            
            # Send to vision model
            response = send_to_vision_model(str(output_image_path), system_prompt=enhanced_prompt)
            
            # Parse and convert grid references
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
