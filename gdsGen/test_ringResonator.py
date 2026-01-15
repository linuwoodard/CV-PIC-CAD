import gdsfactory as gf
from pathlib import Path
from pdk import ring_resonator

def test_rings():
    c = gf.Component("Ring_Test_Array")
    
    # 1. Setup Output Path
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "gdsOutputs"
    output_dir.mkdir(exist_ok=True)
    
    # 2. Create Components
    # Case 1: Double Sided (Default)
    r1 = c << ring_resonator(radius=100.0, isDoubleSided=True)
    r1.x = 0
    
    # Case 2: Single Sided (Phantom Ports)
    r2 = c << ring_resonator(radius=100.0, isDoubleSided=False)
    r2.x = 500
    
    # 3. Verify Ports
    print("[INFO] Checking ports on Single-Sided Ring...")
    
    # FIX: 'p' is the Port object itself, not the name string.
    for p in r2.ports:
        # Access properties directly on 'p'
        print(f"  - Port {p.name}: {p.center}")
        
    # Check for specific port names by creating a list of names first
    port_names = [p.name for p in r2.ports]
    
    if "o3" in port_names and "o4" in port_names:
        print("[SUCCESS] Single-sided ring has phantom ports o3/o4.")
    else:
        print(f"[FAILURE] Missing ports. Found: {port_names}")

    # 4. Save GDS
    gds_path = output_dir / "ring_resonator_test.gds"
    c.write_gds(gds_path)
    print(f"[SUCCESS] GDS saved to: {gds_path}")
    
    # 5. Show
    c.show()

if __name__ == "__main__":
    test_rings()


    import numpy as np
import gdsfactory as gf
from gdsfactory.typings import LayerSpec

# --- Helper Math Function (Mimics genFocusingStripe_LiSa) ---
def _gen_focusing_stripe(
    q: int,
    neff: float,
    theta_deg: float,
    w: float,
    theta_opening_deg: float,
    lambda0: float = 1.55,
    n_env: float = 1.44
):
    """
    Generates the polygon points for a single focusing grating arc.
    Math ported directly from MATLAB 'genFocusingStripe_LiSa'.
    """
    N = 40  # Resolution
    phis = np.linspace(-theta_opening_deg/2, theta_opening_deg/2, N)
    
    # Pre-calculate constants
    sin_theta = np.sin(np.radians(theta_deg))
    
    # 1. Left Arc (Inner radius of the hole)
    points_left = []
    for phi_deg in phis:
        phi = np.radians(phi_deg)
        # Radius equation from reference
        r = (q * lambda0) / (neff - n_env * np.cos(phi) * sin_theta)
        
        # Convert to Cartesian (Focus is at 0,0)
        # In MATLAB: p = [r*cosd(phi) - r - w/2; r*sind(phi)];
        # The '-r' term shifts it so the curve center is near x=0 relative to the radius? 
        # Actually, looking at the MATLAB code: 
        #   myArc.translate(curr_x + pitch, curr_y) where curr_x starts at 0.
        #   The loop uses q_min + ii.
        # Let's trust the coordinate transform: x = r*cos(phi) - r
        # This puts the "center" of the arc at x = -w/2 relative to 'r'
        
        x = r * np.cos(phi) - r - w/2
        y = r * np.sin(phi)
        points_left.append((x, y))
        
    # 2. Right Arc (Outer radius of the hole)
    points_right = []
    # Iterate backwards to close the polygon loop cleanly
    for phi_deg in reversed(phis):
        phi = np.radians(phi_deg)
        r = (q * lambda0) / (neff - n_env * np.cos(phi) * sin_theta)
        
        x = r * np.cos(phi) - r + w/2
        y = r * np.sin(phi)
        points_right.append((x, y))
        
    return points_left + points_right

# --- Main Component ---
@gf.cell
def focusing_grating_coupler(
    pitch: float = 1.16,
    n_periods: int = 30,
    duty_cycle_start: float = 0.8,
    duty_cycle_end: float = 0.42,
    wg_width: float = 1.2,
    taper_width: float = 1.0,  # Width at the grating interface
    focusing_length: float = 37.5,
    defocus: float = -8.0,
    grating_width: float = 20.0,
    theta_deg: float = 20.0,
    theta_opening_deg: float = 30.0,
    lambda0: float = 1.55,
    layer: LayerSpec = (1, 0),
    **kwargs
) -> gf.Component:
    """
    Focusing Grating Coupler matching MATLAB 'focusing_gratingcoupler_LiSa'.
    
    Structure:
    [Tapered WG] -> [Focusing Fanout Region] with [Etched Holes]
    """
    c = gf.Component()

    # 1. Calculate derived parameters
    # Effective index assumption from MATLAB code:
    # neff = lambda0/pitch + sind(theta)
    neff = lambda0/pitch + np.sin(np.radians(theta_deg))
    
    # q_min calculation from MATLAB
    # q_min = round(focusing_length*(neff - sind(theta))/lambda0)
    q_min = round(focusing_length * (neff - np.sin(np.radians(theta_deg))) / lambda0)
    
    # Duty cycle array (linear taper)
    duty_cycles = np.linspace(duty_cycle_start, duty_cycle_end, n_periods)

    # 2. Generate the Fanout Body (The solid Silicon slab)
    # The body is a trapezoid/wedge defined by the grating width and opening angle
    # We construct it large enough to hold all holes.
    
    # Calculate total grating length to determine fanout size
    total_grating_len = pitch * n_periods
    L_total = focusing_length + defocus + total_grating_len
    
    # Vertices for the fanout body (Trapezoid)
    # Start at the taper interface (x=0)
    # End at L_total
    
    # To match MATLAB 'dev_pts', it seems to define a simple trapezoid:
    # pts{1} = [0; -taper_width/2]
    # pts{2} = [L; -W/2] ...
    
    # Note: In MATLAB code, the holes are generated relative to a focus, 
    # then translated. We need to align the body to the holes.
    # The MATLAB code translates the holes by [focusing_length + defocus; 0]
    
    # Let's create the solid body first
    fanout_pts = [
        (0, -taper_width/2),
        (L_total, -grating_width/2),
        (L_total, grating_width/2),
        (0, taper_width/2)
    ]
    fanout_poly = gf.Polygon(fanout_pts)
    
    # 3. Generate Holes
    holes = []
    
    curr_x = 0 # Relative to start of grating section
    
    # Offset to align with the MATLAB translation
    # MATLAB: hole_group.translate([focusing_length + defocus - small_buffer; 0]);
    # The small_buffer is 1.5 in the code.
    small_buffer = 1.5
    hole_origin_x = focusing_length + defocus - small_buffer
    
    for i in range(n_periods):
        # MATLAB: w = (1 - duty_cycle) * pitch
        # This 'w' is the width of the HOLE (etched area)
        dc = duty_cycles[i]
        w_hole = (1.0 - dc) * pitch
        
        # q index for the curve equation
        q = q_min + (i + 1)
        
        # Generate points
        pts = _gen_focusing_stripe(q, neff, theta_deg, w_hole, theta_opening_deg, lambda0)
        
        # Create Polygon
        h = gf.Polygon(pts)
        
        # Translate to correct position
        # In MATLAB, the arc generator centers it.
        # Then loop translates by (curr_x + pitch).
        # Then group translates by (focusing_length + defocus).
        
        shift_x = hole_origin_x + curr_x + pitch
        h.movex(shift_x)
        holes.append(h)
        
        curr_x += pitch

    # 4. Boolean Subtract: Material = Fanout - Holes
    # We merge all holes into one region for cleaner boolean
    final_shape = gf.geometry.boolean(
        A=fanout_poly,
        B=holes,
        operation="not",
        layer=layer
    )
    c.add_ref(final_shape)

    # 5. Add Input Taper (Waveguide connection)
    # MATLAB: wg_max_len = 100. wg_length = wg_max_len - L.
    # It creates a taper from wg_width (1.2) to taper_width (1.0).
    wg_max_len = 100.0
    input_taper_len = max(10.0, wg_max_len - L_total) # Ensure it's not negative
    
    taper = gf.components.taper(
        length=input_taper_len,
        width1=wg_width,
        width2=taper_width,
        layer=layer
    )
    t_ref = c << taper
    # Taper connects to the left side of the fanout (x=0)
    # The taper component center is usually in the middle or starts at 0.
    # gf.components.taper ports are 'o1' (left, width1) and 'o2' (right, width2).
    # We want o2 to connect to fanout at (0,0).
    t_ref.connect("o2", destination=c.add_port("temp", center=(0,0), width=taper_width, orientation=180, layer=layer))
    
    # 6. Expose Port
    c.add_port("o1", port=t_ref.ports["o1"])
    c.remove_ports("temp")

    return c