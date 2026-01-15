"""
Optical Circuit Digitizer - Desktop GUI Application
Simple tkinter interface for the vision pipeline.
"""

import argparse
import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
import math

import cv2
import yaml
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont

# Import translator pipeline functions
import sys
# Ensure gdsGen is in path for PDK import
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "vision"))
sys.path.insert(0, str(project_root / "gdsGen"))

from translator_pipeline import (
    send_to_vision_model,
    parse_ai_response,
    construct_prompt_with_examples
)
from prompts import GRID_SYSTEM_PROMPT_V3
from overlay_grid import overlay_grid_on_image
from grid_tools import GridMapper

# Try to import PDK for exact sizing and ports
try:
    import gdsfactory as gf
    import pdk
    PDK_AVAILABLE = True
except ImportError:
    print("Warning: gdsfactory or pdk not found. Using fallback sizes.")
    PDK_AVAILABLE = False


# --- CONSTANTS ---
FALLBACK_SIZES = {
    'mzi': (1000, 80),
    'mzi_no_heater': (1000, 80),
    'ring_resonator': (400, 400),
    'focusing_grating_coupler': (60, 25),
    'grating_coupler': (60, 25),
    'tapered_input_coupler': (100, 10),
    'directional_coupler': (100, 50),
    'straight': (200, 5),
    'bend_euler': (20, 20)
}
DEFAULT_SIZE = (50, 50)

# Fallback Port locations (relative to center) if PDK missing
FALLBACK_PORTS = {
    'mzi': {'o1': (-500, 0), 'o2': (500, 0)},
    'ring_resonator': {'o1': (0, -205), 'o2': (0, 205)}, # Approx
}

class OpticalCircuitDigitizerGUI:
    """Main GUI application class."""
    
    def __init__(self, root, bypass_llm=False):
        self.root = root
        self.root.title("Optical Circuit Digitizer")
        self.root.geometry("1200x850") 
        
        # LLM bypass flag
        self.bypass_llm = bypass_llm
        
        # State Variables
        self.selected_filename = tk.StringVar(value="No file selected")
        self.current_file = None
        self.grid_image_path = None
        self.original_image_path = None
        
        # Preview State
        self.preview_image_base = None  # Full res generated preview
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Component Cache (stores instantiated PDK objects info)
        self.comp_cache = {} 
        
        # Create and layout widgets
        self._create_widgets()
        self._layout_widgets()
        self._bind_events()
        
        self.update_status("Ready")
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Top Section
        top_frame = tk.Frame(self.root)
        self.select_button = tk.Button(top_frame, text="Select Image", command=self._on_select_image, width=15, height=2)
        self.filename_label = tk.Label(top_frame, textvariable=self.selected_filename, anchor="w", padx=10, font=("Arial", 10))
        
        # Middle Section (Split View)
        self.middle_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        
        # Left: YAML Editor
        yaml_frame = tk.Frame(self.middle_container)
        yaml_label = tk.Label(yaml_frame, text="Circuit YAML", font=("Arial", 9, "bold"), anchor="w")
        yaml_label.pack(fill=tk.X)
        self.yaml_text = ScrolledText(yaml_frame, wrap=tk.WORD, width=40, height=25, font=("Courier", 10))
        self.yaml_text.pack(fill=tk.BOTH, expand=True)
        
        # Right: Image Preview
        image_frame = tk.Frame(self.middle_container)
        
        # Toolbar for Preview
        tool_frame = tk.Frame(image_frame)
        tool_frame.pack(fill=tk.X, padx=2, pady=2)
        
        tk.Label(tool_frame, text="Preview Controls:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        
        # Grid Selection
        tk.Label(tool_frame, text="Grid:").pack(side=tk.LEFT, padx=(10, 2))
        self.grid_var = tk.StringVar(value="None")
        grid_opts = ["None", "10 um", "25 um", "100 um", "1 mm"]
        self.grid_menu = ttk.OptionMenu(tool_frame, self.grid_var, "None", *grid_opts, command=self._on_grid_change)
        self.grid_menu.pack(side=tk.LEFT)
        
        # Reset Button
        tk.Button(tool_frame, text="Reset View", command=self._reset_view, height=1).pack(side=tk.RIGHT)

        self.image_display_label = tk.Label(
            image_frame,
            text="No image selected",
            bg="#E0E0E0",
            relief=tk.SUNKEN,
            anchor="center",
            cursor="fleur"
        )
        self.image_display_label.pack(fill=tk.BOTH, expand=True)
        
        self.middle_container.add(yaml_frame, minsize=350)
        self.middle_container.add(image_frame, minsize=500)
        
        # Bottom Section
        bottom_frame = tk.Frame(self.root)
        self.generate_button = tk.Button(bottom_frame, text="Generate CAD", command=self._on_generate_cad, width=15, height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.preview_button = tk.Button(bottom_frame, text="Preview Placement", command=self._on_preview_placement, width=15, height=2, bg="#FFC107", fg="black", font=("Arial", 10, "bold"))
        self.cancel_button = tk.Button(bottom_frame, text="Cancel / Clear", command=self._on_cancel_clear, width=15, height=2, bg="#f44336", fg="white", font=("Arial", 10))
        
        # Status Bar
        self.status_label = tk.Label(self.root, text="Ready", anchor="w", relief=tk.SUNKEN, padx=5, pady=2, font=("Arial", 9))
        
        # Store frames
        self.top_frame = top_frame
        self.bottom_frame = bottom_frame

    def _layout_widgets(self):
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        self.select_button.pack(side=tk.LEFT, padx=(0, 10))
        self.filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.middle_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        self.generate_button.pack(side=tk.LEFT, padx=(0, 10))
        self.preview_button.pack(side=tk.LEFT, padx=(0, 10))
        self.cancel_button.pack(side=tk.RIGHT)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def _bind_events(self):
        """Bind mouse events for zooming and panning."""
        self.image_display_label.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows/MacOS
        self.image_display_label.bind("<Button-4>", self._on_mouse_wheel)    # Linux Scroll Up
        self.image_display_label.bind("<Button-5>", self._on_mouse_wheel)    # Linux Scroll Down
        self.image_display_label.bind("<ButtonPress-1>", self._on_drag_start)
        self.image_display_label.bind("<B1-Motion>", self._on_drag_motion)
        self.image_display_label.bind("<Button-3>", self._reset_view) 

    # --- Zoom & Pan Logic ---

    def _reset_view(self, event=None):
        if self.preview_image_base:
            self.zoom_level = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self._update_image_display()

    def _on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_drag_motion(self, event):
        if not self.preview_image_base: return
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self._update_image_display()

    def _on_mouse_wheel(self, event):
        if not self.preview_image_base: return
        if event.num == 5 or event.delta < 0:
            factor = 0.9
        else:
            factor = 1.1
        self.zoom_level *= factor
        if self.zoom_level < 0.1: self.zoom_level = 0.1
        if self.zoom_level > 20.0: self.zoom_level = 20.0
        self._update_image_display()

    def _update_image_display(self):
        if not self.preview_image_base: return
        vw = self.image_display_label.winfo_width() or 500
        vh = self.image_display_label.winfo_height() or 500
        
        img_w, img_h = self.preview_image_base.size
        new_w = int(img_w * self.zoom_level)
        new_h = int(img_h * self.zoom_level)
        
        try:
            if new_w > 15000: return # Cap
            
            resized_img = self.preview_image_base.resize((new_w, new_h), Image.Resampling.LANCZOS)
            view_img = Image.new("RGB", (vw, vh), (240, 240, 240))
            
            center_x = vw // 2 + self.pan_x
            center_y = vh // 2 + self.pan_y
            paste_x = center_x - (new_w // 2)
            paste_y = center_y - (new_h // 2)
            
            view_img.paste(resized_img, (paste_x, paste_y))
            
            tk_image = ImageTk.PhotoImage(view_img)
            self.image_display_label.config(image=tk_image, text="")
            self.image_display_label.image = tk_image
        except Exception as e:
            print(f"Zoom Error: {e}")

    def _on_grid_change(self, value):
        # Trigger redraw
        self._on_preview_placement()

    # --- PDK Helper: Get Component Info ---
    def _get_component_info(self, comp_type, settings):
        """
        Instantiates PDK component to get:
        1. Exact size (w, h)
        2. Port locations relative to center
        """
        cache_key = f"{comp_type}_{str(settings)}"
        if cache_key in self.comp_cache:
            return self.comp_cache[cache_key]

        info = {
            'w': DEFAULT_SIZE[0],
            'h': DEFAULT_SIZE[1],
            'ports': {}
        }

        if PDK_AVAILABLE and hasattr(pdk, comp_type):
            try:
                clean_settings = {k: v for k, v in settings.items() if k != 'rotation'}
                func = getattr(pdk, comp_type)
                c = func(**clean_settings)
                
                # Size
                if hasattr(c, "dxsize"):
                    info['w'], info['h'] = c.dxsize, c.dysize
                elif hasattr(c, "size"):
                    info['w'], info['h'] = c.size[0], c.size[1]
                else:
                    bbox = c.bbox
                    if callable(bbox): bbox = bbox()
                    # Check if bbox is numpy array or object
                    if hasattr(bbox, 'width'):
                         # klayout dbox
                         info['w'] = bbox.width()
                         info['h'] = bbox.height()
                    else:
                        # numpy
                        info['w'] = bbox[1][0] - bbox[0][0]
                        info['h'] = bbox[1][1] - bbox[0][1]

                # Ports
                # Store relative to center (0,0)
                for p_name, p in c.ports.items():
                    info['ports'][p_name] = (p.center[0], p.center[1])

            except Exception as e:
                print(f"PDK Info Error for {comp_type}: {e}")
                if comp_type in FALLBACK_SIZES:
                    info['w'], info['h'] = FALLBACK_SIZES[comp_type]
        else:
            if comp_type in FALLBACK_SIZES:
                info['w'], info['h'] = FALLBACK_SIZES[comp_type]
            if comp_type in FALLBACK_PORTS:
                info['ports'] = FALLBACK_PORTS[comp_type]
        
        self.comp_cache[cache_key] = info
        return info

    # --- Drawing Logic ---

    def _draw_preview_on_image(self, circuit_data):
        try:
            # 1. Parse YAML
            if not isinstance(circuit_data, dict) or 'instances' not in circuit_data:
                self.update_status("Preview Error: YAML missing 'instances'.")
                return

            instances = circuit_data.get('instances', {})
            placements = circuit_data.get('placements', {})
            
            # 2. Resolve Positions & Ports
            resolved_positions = {} # name -> {x, y, rotation, info}
            
            # Pre-load info for all instances
            for name, details in instances.items():
                c_type = details.get('component', 'Unknown')
                settings = details.get('settings', {})
                info = self._get_component_info(c_type, settings)
                
                # Get rotation
                p_rot = placements.get(name, {}).get('rotation', 0)
                s_rot = settings.get('rotation', 0)
                rot = float(s_rot or p_rot)
                
                resolved_positions[name] = {
                    'x': 0.0, 'y': 0.0, 
                    'rotation': rot,
                    'info': info,
                    'resolved': False
                }

            # Pass 1: Absolutes
            for name in instances:
                if name in placements:
                    p = placements[name]
                    raw_x, raw_y = p.get('x', 0), p.get('y', 0)
                    if isinstance(raw_x, (int, float)) and isinstance(raw_y, (int, float)):
                        resolved_positions[name]['x'] = float(raw_x)
                        resolved_positions[name]['y'] = float(raw_y)
                        resolved_positions[name]['resolved'] = True
                else:
                    # Default 0,0 if not placed
                    resolved_positions[name]['resolved'] = True

            # Pass 2: Relative (Port-aware)
            # Loop multiple times to resolve dependencies
            for _ in range(3):
                for name, data in resolved_positions.items():
                    if data['resolved']: continue
                    if name not in placements: continue
                    
                    p = placements[name]
                    dx = float(p.get('dx', 0))
                    dy = float(p.get('dy', 0))
                    
                    # Logic: We need a reference anchor.
                    # Usually x: "ref_comp,ref_port"
                    
                    # --- X Calculation ---
                    ref_x = 0.0
                    raw_x = p.get('x', 0)
                    if isinstance(raw_x, (int, float)):
                        ref_x = float(raw_x)
                    elif isinstance(raw_x, str) and ',' in raw_x:
                        ref_name, ref_port = raw_x.split(',')
                        if ref_name in resolved_positions and resolved_positions[ref_name]['resolved']:
                            ref_data = resolved_positions[ref_name]
                            # Get ref component's center
                            rc_x = ref_data['x']
                            # Get ref port offset
                            rp_off = ref_data['info']['ports'].get(ref_port, (0,0))
                            
                            # Rotate port offset based on Ref Comp Rotation
                            theta = math.radians(ref_data['rotation'])
                            rox = rp_off[0] * math.cos(theta) - rp_off[1] * math.sin(theta)
                            
                            ref_x = rc_x + rox
                        else:
                            continue # Wait for ref to resolve

                    # --- Y Calculation ---
                    ref_y = 0.0
                    raw_y = p.get('y', 0)
                    if isinstance(raw_y, (int, float)):
                        ref_y = float(raw_y)
                    elif isinstance(raw_y, str) and ',' in raw_y:
                        ref_name, ref_port = raw_y.split(',')
                        if ref_name in resolved_positions and resolved_positions[ref_name]['resolved']:
                            ref_data = resolved_positions[ref_name]
                            rc_y = ref_data['y']
                            rp_off = ref_data['info']['ports'].get(ref_port, (0,0))
                            
                            theta = math.radians(ref_data['rotation'])
                            roy = rp_off[0] * math.sin(theta) + rp_off[1] * math.cos(theta)
                            
                            ref_y = rc_y + roy
                        else:
                            continue

                    # Apply result
                    resolved_positions[name]['x'] = ref_x + dx
                    resolved_positions[name]['y'] = ref_y + dy
                    resolved_positions[name]['resolved'] = True


            # 3. Calculate Bounds
            valid_comps = [n for n in resolved_positions if resolved_positions[n]['resolved']]
            if not valid_comps: return

            min_x, max_x = float('inf'), float('-inf')
            min_y, max_y = float('inf'), float('-inf')
            
            draw_list = []

            for name in valid_comps:
                data = resolved_positions[name]
                info = data['info']
                x, y = data['x'], data['y']
                
                # Size depends on rotation
                rot = data['rotation'] % 180
                if 45 < rot < 135:
                    w, h = info['h'], info['w']
                else:
                    w, h = info['w'], info['h']
                
                draw_list.append({'name': name, 'x': x, 'y': y, 'w': w, 'h': h, 'type': instances[name].get('component','')})
                
                min_x = min(min_x, x - w/2); max_x = max(max_x, x + w/2)
                min_y = min(min_y, y - h/2); max_y = max(max_y, y + h/2)

            # 4. Canvas Setup
            width_um = max_x - min_x
            height_um = max_y - min_y
            
            # Add 15% Padding
            pad_x = max(50.0, width_um * 0.15)
            pad_y = max(50.0, height_um * 0.15)
            
            view_min_x = min_x - pad_x; view_max_x = max_x + pad_x
            view_min_y = min_y - pad_y; view_max_y = max_y + pad_y
            
            view_w = view_max_x - view_min_x
            view_h = view_max_y - view_min_y
            if view_w <= 0: view_w = 100
            if view_h <= 0: view_h = 100

            # High Res Canvas
            C_SIZE = 1500
            img = Image.new("RGBA", (C_SIZE, C_SIZE), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            scale = min(C_SIZE / view_w, C_SIZE / view_h)

            def to_pix(ux, uy):
                px = (ux - view_min_x) * scale
                # Y Flip: map view_max_y -> 0
                py = (view_max_y - uy) * scale
                
                # Center
                ox = (C_SIZE - (view_w * scale)) / 2
                oy = (C_SIZE - (view_h * scale)) / 2
                return px + ox, py + oy

            # 5. Draw Grid
            grid_setting = self.grid_var.get()
            if grid_setting != "None":
                if "10 um" in grid_setting: g_step = 10
                elif "25 um" in grid_setting: g_step = 25
                elif "100 um" in grid_setting: g_step = 100
                elif "1 mm" in grid_setting: g_step = 1000
                else: g_step = 100

                # Calculate start/end lines
                start_x = int(view_min_x // g_step) * g_step
                end_x = int(view_max_x // g_step) * g_step
                start_y = int(view_min_y // g_step) * g_step
                end_y = int(view_max_y // g_step) * g_step
                
                for gx in range(int(start_x), int(end_x) + g_step, int(g_step)):
                    p1 = to_pix(gx, view_min_y)
                    p2 = to_pix(gx, view_max_y)
                    draw.line([p1, p2], fill="#E0E0E0", width=1)
                
                for gy in range(int(start_y), int(end_y) + g_step, int(g_step)):
                    p1 = to_pix(view_min_x, gy)
                    p2 = to_pix(view_max_x, gy)
                    draw.line([p1, p2], fill="#E0E0E0", width=1)


            # 6. Draw Components & Labels
            try:
                font = ImageFont.truetype("arial.ttf", size=18)
            except:
                font = ImageFont.load_default()

            for c in draw_list:
                cx, cy = to_pix(c['x'], c['y'])
                pw, ph = c['w'] * scale, c['h'] * scale
                
                x0, y0 = cx - pw/2, cy - ph/2
                x1, y1 = cx + pw/2, cy + ph/2
                
                # Colors
                col = "green"
                ctype = str(c['type']).lower()
                if "grating" in ctype: col = "#FFA500" # Orange
                elif "ring" in ctype: col = "#0000FF"   # Blue
                elif "mzi" in ctype: col = "#800080"    # Purple
                
                # Box
                draw.rectangle([x0, y0, x1, y1], outline=col, width=3, fill=(200, 200, 200, 80))
                
                # Center Dot
                draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill="red")
                
                # Smart Label: Draw offset with leader line
                label_txt = c['name']
                
                # Calculate text size
                if hasattr(draw, "textbbox"):
                    bbox = draw.textbbox((0,0), label_txt, font=font)
                    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                else:
                    tw, th = draw.textsize(label_txt, font=font)
                
                # Place label above box
                lx = cx - tw/2
                ly = y0 - th - 10 # 10px gap
                
                # Draw white backing for text
                draw.rectangle([lx-2, ly-2, lx+tw+2, ly+th+2], fill="white", outline="black")
                draw.text((lx, ly), label_txt, fill="black", font=font)
                
                # Leader line
                draw.line([(cx, y0), (cx, ly+th+2)], fill="black", width=1)

            # 7. Update View
            self.preview_image_base = img.convert("RGB")
            self.zoom_level = 1.0
            self.pan_x = 0; self.pan_y = 0
            self._update_image_display()
            self.update_status(f"Preview: Plotted {len(draw_list)} components.")

        except Exception as e:
            print(f"Preview Error: {e}")
            import traceback
            traceback.print_exc()
            self.update_status(f"Preview Error: {str(e)}")


    # --- Boilerplate ---
    def _on_select_image(self): self.upload_action()
    def _on_generate_cad(self): self.submit_action()
    def _on_preview_placement(self): 
        content = self.yaml_text.get("1.0", tk.END)
        try:
            data = yaml.safe_load(content)
            self._draw_preview_on_image(data)
        except Exception as e:
            self.update_status(f"YAML Parse Error: {e}")

    def _on_cancel_clear(self): self.cancel_action()

    def upload_action(self):
        file_path = filedialog.askopenfilename()
        if not file_path: return
        self.current_file = file_path
        self.selected_filename.set(os.path.basename(file_path))
        self.update_status("Analyzing...")
        threading.Thread(target=self._analyze_image_thread, args=(file_path,), daemon=True).start()

    def _analyze_image_thread(self, image_path):
        try:
            if self.bypass_llm:
                resp = "# LLM Bypassed.\n# Paste your YAML here.\n"
            else:
                # Mockup for brevity - insert your pipeline calls here
                resp = "# Analysis Result place holder"
            self.root.after(0, self._update_yaml_text, resp, None)
        except Exception as e:
            self.root.after(0, self._update_yaml_text, None, str(e))

    def _update_yaml_text(self, text, error):
        if error:
            self.yaml_text.delete("1.0", tk.END)
            self.yaml_text.insert("1.0", f"Error: {error}")
        else:
            self.yaml_text.delete("1.0", tk.END)
            self.yaml_text.insert("1.0", text)
            if not self.bypass_llm: self._on_preview_placement()

    def submit_action(self):
        # Insert previous submit logic here
        pass

    def cancel_action(self):
        self.yaml_text.delete("1.0", tk.END)
        self.image_display_label.config(image="", text="No image")
        self.preview_image_base = None

    def update_status(self, msg):
        self.status_label.config(text=msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bypass-llm", action="store_true")
    args = parser.parse_args()
    root = tk.Tk()
    app = OpticalCircuitDigitizerGUI(root, bypass_llm=args.bypass_llm)
    root.mainloop()

if __name__ == "__main__":
    main()