import gdsfactory as gf
from pathlib import Path
from functools import partial
from pdk import mzi_no_heater, tapered_input_coupler

def build_gds():
    # 1. Resolve Paths
    script_dir = Path(__file__).parent
    yaml_path = script_dir.parent / "output" / "circuit_redux2.yaml"
    output_dir = script_dir.parent / "gdsOutputs"

    if not yaml_path.exists():
        print(f"❌ Error: YAML file not found at: {yaml_path.absolute()}")
        return

    output_dir.mkdir(exist_ok=True)

    # 2. Define Custom Cross-Section (1.2um wide strip)
    # We use 'partial' to create a pre-configured version of the strip function
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
    print(f"📖 Reading circuit from: {yaml_path.name}...")
    c = gf.read.from_yaml(str(yaml_path))

    # 5. Save and Show
    output_gds = output_dir / yaml_path.with_suffix(".gds").name
    c.write_gds(output_gds)
    c.show()
    
    print(f"✅ Success! GDS saved to: {output_gds}")

if __name__ == "__main__":
    build_gds()