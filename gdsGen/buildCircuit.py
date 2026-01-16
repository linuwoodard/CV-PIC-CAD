import sys
import yaml
import gdsfactory as gf
from pathlib import Path
from functools import partial
from pdk import *

def build_circuit_from_dict(circuit_data: dict, pdk, strip_1p2=None, unique_suffix=None):
    """
    Build a gdsfactory Component from a circuit dictionary.
    Handles both absolute (anchor) and relative placements.
    
    Args:
        circuit_data: Dictionary containing instances, placements, and routes
        pdk: Active PDK object
        strip_1p2: Custom cross-section for 1.2um strip (optional)
        unique_suffix: Optional suffix to append to circuit name to make it unique
    """
    # Create a new component
    circuit_name = circuit_data.get('name', 'circuit')
    # Make name unique by appending suffix if provided
    if unique_suffix:
        circuit_name = f"{circuit_name}_{unique_suffix}"
    c = gf.Component(name=circuit_name)
    
    # Get instances and placements
    instances = circuit_data.get('instances', {})
    placements = circuit_data.get('placements', {})
    
    # Dictionary to store component references
    component_refs = {}
    
    # First pass: Create all component instances
    for instance_name, instance_data in instances.items():
        component_type = instance_data.get('component')
        settings = instance_data.get('settings', {})
        
        # Get the component factory from PDK
        # Try PDK get_cell method first (standard gdsfactory PDK API)
        component_factory = None
        try:
            component_factory = pdk.get_cell(component_type)
        except (AttributeError, KeyError):
            pass
        
        # Try PDK cells dictionary if available
        if component_factory is None and hasattr(pdk, 'cells'):
            component_factory = pdk.cells.get(component_type)
        
        # Fallback: try to get from gdsfactory components
        if component_factory is None:
            component_factory = getattr(gf.components, component_type, None)
        
        if component_factory is None:
            raise ValueError(f"Component type '{component_type}' not found in PDK or gdsfactory")
        
        # Create the component instance
        if settings:
            comp = component_factory(**settings)
        else:
            comp = component_factory()
        
        # Add to component
        ref = c.add_ref(comp, name=instance_name)
        component_refs[instance_name] = ref
    
    # Second pass: Place components (anchor first, then relative)
    # Separate anchor and relative placements
    anchor_placements = {}
    relative_placements = {}
    
    for instance_name, placement_data in placements.items():
        if 'to' in placement_data:
            relative_placements[instance_name] = placement_data
        else:
            anchor_placements[instance_name] = placement_data
    
    # Place anchor components first
    for instance_name, placement_data in anchor_placements.items():
        if instance_name not in component_refs:
            print(f"[WARNING] Instance '{instance_name}' not found in instances, skipping placement")
            continue
        
        ref = component_refs[instance_name]
        x = placement_data.get('x', 0)
        y = placement_data.get('y', 0)
        rotation = placement_data.get('rotation', 0)
        
        # Validate that x and y are numbers (not strings like "mzi_1,o2")
        try:
            x = float(x)
            y = float(y)
        except (ValueError, TypeError):
            print(f"[ERROR] Invalid placement for '{instance_name}': x={x}, y={y}. Expected numeric values for anchor placement.")
            print(f"[ERROR] If you intended relative placement, use 'to: instance,port' syntax instead of 'x: instance,port'")
            continue
        
        # Move to absolute position
        ref.move((x, y))
        if rotation != 0:
            ref.rotate(rotation)
    
    # Place relative components
    for instance_name, placement_data in relative_placements.items():
        if instance_name not in component_refs:
            print(f"[WARNING] Instance '{instance_name}' not found in instances, skipping placement")
            continue
        
        ref = component_refs[instance_name]
        
        # Parse the 'to' string: "target_instance,target_port"
        to_str = placement_data.get('to', '')
        if ',' not in to_str:
            print(f"[WARNING] Invalid 'to' format for '{instance_name}': {to_str}. Expected 'instance,port'")
            continue
        
        target_instance_name, target_port = to_str.split(',', 1)
        target_port = target_port.strip()
        
        if target_instance_name not in component_refs:
            print(f"[WARNING] Target instance '{target_instance_name}' not found for '{instance_name}'")
            continue
        
        target_ref = component_refs[target_instance_name]
        my_port = placement_data.get('port', 'o1')
        dx = placement_data.get('dx', 0)
        dy = placement_data.get('dy', 0)
        rotation = placement_data.get('rotation', 0)
        
        # Connect to target port
        try:
            # Get the target port position
            if target_port not in target_ref.ports:
                print(f"[WARNING] Port '{target_port}' not found on '{target_instance_name}'")
                continue
            
            # Connect this component's port to the target port
            ref.connect(my_port, target_ref.ports[target_port])
            
            # Apply relative offset after connection
            if dx != 0 or dy != 0:
                ref.move((dx, dy))
            
            # Apply rotation
            if rotation != 0:
                ref.rotate(rotation)
                
        except Exception as e:
            print(f"[WARNING] Failed to connect '{instance_name}' to '{target_instance_name}': {e}")
            continue
    
    # Third pass: Add routes
    routes = circuit_data.get('routes', {})
    for route_name, route_data in routes.items():
        links = route_data.get('links', {})
        route_settings = route_data.get('settings', {})
        
        for link_str, target_str in links.items():
            # Parse link: "instance,port"
            if ',' not in link_str:
                continue
            source_instance, source_port = link_str.split(',', 1)
            source_port = source_port.strip()
            
            if ',' not in target_str:
                continue
            target_instance, target_port = target_str.split(',', 1)
            target_port = target_port.strip()
            
            if source_instance not in component_refs or target_instance not in component_refs:
                continue
            
            source_ref = component_refs[source_instance]
            target_ref = component_refs[target_instance]
            
            # Get cross-section
            cross_section_name = route_settings.get('cross_section', 'strip_1p2')
            cross_section = None
            
            # Try PDK get_cross_section method first
            try:
                cross_section = pdk.get_cross_section(cross_section_name)
            except (AttributeError, KeyError):
                pass
            
            # Try PDK cross_sections dictionary if available
            if cross_section is None and hasattr(pdk, 'cross_sections'):
                cross_section = pdk.cross_sections.get(cross_section_name)
            
            # Fallback to default strip
            if cross_section is None:
                if cross_section_name == 'strip_1p2' and strip_1p2 is not None:
                    cross_section = strip_1p2  # Use the registered cross-section
                else:
                    cross_section = gf.cross_section.strip()
            
            # Create route using route_single (gdsfactory v8+ API)
            try:
                # route_single automatically adds the route to the component
                gf.routing.route_single(
                    c,  # Component to add route to
                    source_ref.ports[source_port],
                    target_ref.ports[target_port],
                    cross_section=cross_section
                )
            except Exception as e:
                print(f"[WARNING] Failed to create route from '{source_instance},{source_port}' to '{target_instance},{target_port}': {e}")
    
    return c

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
        tapered_input_coupler=tapered_input_coupler,
        euler_bend=euler_bend,
        racetrack_resonator=racetrack_resonator,
        ring_resonator=ring_resonator,
        focusing_grating_coupler=focusing_grating_coupler
    )
    
    # Register Cross-Sections
    pdk.register_cross_sections(strip_1p2=strip_1p2)

    # 4. Generate Circuit
    print(f"[INFO] Reading circuit from: {input_path.name}...")
    try:
        # Load YAML manually to handle relative placements
        with open(input_path, 'r', encoding='utf-8') as f:
            circuit_data = yaml.safe_load(f)
        
        # Build circuit manually to support relative placements
        # Use input filename (without extension) as unique suffix to avoid name conflicts
        unique_suffix = input_path.stem
        c = build_circuit_from_dict(circuit_data, pdk, strip_1p2, unique_suffix=unique_suffix)
    except Exception as e:
        print(f"[ERROR] Error parsing YAML: {e}")
        import traceback
        traceback.print_exc()
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