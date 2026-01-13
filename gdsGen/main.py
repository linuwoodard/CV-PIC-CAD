"""Main script to generate GDS files from YAML circuit templates."""

import gdsfactory as gf
from pathlib import Path
import sys
import os

# --- Path Handling ---
# Ensures Python can find 'pdk.py' regardless of where you run the script from
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from pdk import CELLS

def build_circuit(yaml_path: str | Path) -> gf.Component:
    """Build a circuit component from a YAML template file."""
    yaml_path = Path(yaml_path)
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    
    # --- THE FIX: Register the PDK ---
    # In GDSFactory 8+, we bundle the cells into a PDK and activate it.
    # This tells the YAML parser where to find 'tapered_input_coupler', etc.
    pdk = gf.Pdk(name="my_custom_fab", cells=CELLS)
    pdk.activate()
    
    # Read the YAML (Notice: no 'cells=' argument anymore)
    print(f"Building from {yaml_path} using Active PDK: {gf.get_active_pdk().name}")
    component = gf.read.from_yaml(yaml_path)
    
    return component

if __name__ == "__main__":
    # Define paths relative to this script
    script_dir = Path(__file__).parent
    
    # Assuming 'template.yaml' is in the SAME folder as main.py
    # If it is in a parent folder, change to: script_dir.parent / "template.yaml"
    template_path = script_dir / "output/circuit.yaml"
    
    # Build the circuit
    try:
        c = build_circuit(template_path)
        
        # Display
        print("Displaying component...")
        c.show()
        
        # Save
        build_dir = script_dir / "build"
        build_dir.mkdir(exist_ok=True)
        output_path = build_dir / "layout.gds"
        c.write_gds(output_path)
        print(f"✅ Success! GDS saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")