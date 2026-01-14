import gdsfactory as gf
from pathlib import Path
from pdk import mzi_no_heater, tapered_input_coupler

def build_gds(circuit_path: str | Path) -> gf.Component:
    # 1. Resolve the File Path
    script_dir = Path(__file__).parent
    circuit_full_path = script_dir / circuit_path

    if not circuit_full_path.exists():
        raise FileNotFoundError(f"Circuit file not found: {circuit_full_path}")

    # 2. Register Components to the Active PDK
    # FIX: Pass them as Keyword Arguments (name=function)
    pdk = gf.get_active_pdk()
    pdk.register_cells(
        mzi_no_heater=mzi_no_heater, 
        tapered_input_coupler=tapered_input_coupler
    )

    # 3. Generate Circuit
    print(f"📖 Reading circuit from: {yaml_path.name}...")
    
    # Now GDSFactory will find the names in the PDK registry
    c = gf.read.from_yaml(str(yaml_path))

    # 4. Save and Show
    output_gds = yaml_path.with_suffix(".gds")
    c.write_gds(output_gds)
    c.show()
    
    print(f"✅ Success! GDS saved to: {output_gds}")

if __name__ == "__main__":
    build_gds("output/circuit.yaml")