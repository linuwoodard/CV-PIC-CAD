import gdsfactory as gf
import yaml

# List the components you are supporting in this project
COMPONENT_LIST = [
    'mzi',
    'straight',
    'bend_euler',
    'grating_coupler_elliptical',
    'ring_single',
    'pad'
]

def generate_port_manifest():
    manifest = {}
    
    for name in COMPONENT_LIST:
        try:
            # Instantiate the component to inspect it
            # (We use default settings for now)
            c = gf.get_component(name)
            
            # Get port names
            port_names = list(c.ports.keys())
            manifest[name] = port_names
            
        except Exception as e:
            print(f"⚠️ Could not load {name}: {e}")

    # Output the "Cheat Sheet" for the AI
    print("\n--- COPY BELOW THIS LINE ---")
    print(yaml.dump(manifest, sort_keys=False))
    print("--- COPY ABOVE THIS LINE ---")

if __name__ == "__main__":
    generate_port_manifest()