import gdsfactory as gf
import pathlib

# Mappings
pdk_map = {
    'mzi': gf.components.mzi,
    'grating_coupler': gf.components.grating_coupler_elliptical,
    'dichroic': gf.components.mmi2x2, # Placeholder
    'racetrack': gf.components.ring_single,
    'edge_coupler': gf.components.taper,
    'pad': gf.components.pad,
    'straight': gf.components.straight,
    'bend_euler': gf.components.bend_euler,
}

if __name__ == "__main__":
    yaml_file = pathlib.Path("templates/template.yaml")
    if yaml_file.exists():
        c = gf.read.from_yaml(yaml_file, cells=pdk_map)
        c.show()
        print("GDS generated successfully.")
    else:
        print(f"File not found: {yaml_file}")
