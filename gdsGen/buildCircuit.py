import sys
import gdsfactory as gf
from pathlib import Path
from functools import partial
from pdk import *

def build_gds(yaml_file_path):
    """
    Builds a GDS from a provided YAML file path.
    """
    # 1. Resolve Paths
    script_dir = Path(__file__).parent
    input_path = Path(yaml_file_path)
    output_dir = script_dir.parent / "gdsOutputs"

    # Handle relative paths correctly (relative to where script is run)
    if not input_path.is_absolute():
        # Try finding it relative to current working directory first
        # If not, try finding it relative to the default 'output' folder
        if not input_path.exists():
             candidate = script_dir.parent / "output" / input_path
             if candidate.exists():
                 input_path = candidate

    if not input_path.exists():
        print(f"[ERROR] YAML file not found at: {input_path.absolute()}")
        return

    output_dir.mkdir(exist_ok=True)

    # 2. Define Custom Cross-Section (1.2um wide strip)
    strip_1p2 = partial(gf.cross_section.strip, width=1.2)

    # 3. Register Everything to the Active PDK
    pdk = gf.get_active_pdk()
    
    # Register Components
    pdk.register_cells(
        mzi_no_heater=mzi_no_heater, 
        tapered_input_coupler=tapered_input_coupler
    )
    
    # Register Cross-Sections
    pdk.register_cross_sections(strip_1p2=strip_1p2)

    # 4. Generate Circuit
    print(f"[INFO] Reading circuit from: {input_path.name}...")
    try:
        c = gf.read.from_yaml(str(input_path))
    except Exception as e:
        print(f"[ERROR] Error parsing YAML: {e}")
        return

    # 5. Save and Show
    output_gds = output_dir / input_path.with_suffix(".gds").name
    c.write_gds(output_gds)
    # c.show() # Optional: Comment out if running in batch/headless mode
    
    print(f"[SUCCESS] GDS saved to: {output_gds}")

if __name__ == "__main__":
    # Check if a filename was provided as a command line argument
    if len(sys.argv) > 1:
        yaml_arg = sys.argv[1]
    else:
        # Default fallback
        script_dir = Path(__file__).parent
        yaml_arg = script_dir.parent / "output" / "circuit_redux.yaml"
        print(f"[INFO] No file argument provided. Defaulting to: {Path(yaml_arg).name}")

    build_gds(yaml_arg)