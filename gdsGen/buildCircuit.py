import gdsfactory as gf
from pathlib import Path
from pdk import mzi_no_heater, tapered_input_coupler

def build_gds(circuit_path: str | Path = None):
    """
    Build GDS file from a YAML circuit definition.
    
    Args:
        circuit_path: Path to the YAML circuit file. If None, defaults to output/circuit.yaml
                      relative to the project root.
    
    Returns:
        gf.Component: The generated circuit component, or None if an error occurred
    """
    # 1. Resolve the File Path
    if circuit_path is None:
        # Default to output/circuit.yaml relative to project root
        script_dir = Path(__file__).parent
        yaml_path = script_dir.parent / "output" / "circuit.yaml"
    else:
        # Use provided path, resolve relative to script directory if it's a relative path
        circuit_path = Path(circuit_path)
        if circuit_path.is_absolute():
            yaml_path = circuit_path
        else:
            # Relative path - resolve relative to gdsGen directory
            project_dir = Path(__file__).parent.parent
            print(f"🔍 Parent directory: {project_dir}")
            yaml_path = project_dir / circuit_path

    if not yaml_path.exists():
        print(f"❌ Error: YAML file not found at: {yaml_path.absolute()}")
        return None

    # 2. Register Components to the Active PDK
    # FIX: Pass them as Keyword Arguments (name=function)
    pdk = gf.get_active_pdk()
    pdk.register_cells(
        mzi_no_heater=mzi_no_heater, 
        tapered_input_coupler=tapered_input_coupler
    )

    # 3. Generate Circuit
    print(f"📖 Reading circuit from: {yaml_path.name}...")
    
    try:
        c = gf.read.from_yaml(str(yaml_path))
        # 4. Save and Show
        output_gds = yaml_path.with_suffix(".gds")
        c.write_gds(output_gds)
        c.show()
        
        print(f"✅ Success! GDS saved to: {output_gds}")
        return c
        
    except Exception as e:
        print(f"❌ Failed to build circuit from YAML file: {yaml_path.name}")
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    build_gds("output/circuit.yaml")