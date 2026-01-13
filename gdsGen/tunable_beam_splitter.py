import gdsfactory as gf
import numpy as np

def create_precise_euler_sbend(cross_section, radius, angle, p, dy_target):
    """
    Manually constructs an Euler S-Bend using Path extrusions.
    Includes UNIT FIX (nm->um) and AUTO-SNAP (fit to gap).
    """
    # A. Define the Euler Spiral Path
    path_bend = gf.path.euler(radius=radius, angle=angle, p=p, use_eff=False)
    
    # B. Extrude it
    bend_c = path_bend.extrude(cross_section)
    
    # C. Measure Height (With Unit Correction)
    if 'o1' in bend_c.ports:
        p1 = bend_c.ports['o1'].center
        p2 = bend_c.ports['o2'].center
    else:
        p1 = bend_c.ports['1'].center
        p2 = bend_c.ports['2'].center

    raw_dy = abs(p2[1] - p1[1])
    
    # Handle DBU scaling
    dbu = 0.001 if raw_dy > 500 else 1.0
    bend_height = raw_dy * dbu
    
    # D. Calculate Straight Section
    min_required_height = 2 * bend_height
    straight_dy_needed = dy_target - min_required_height
    
    # --- AUTO-FIX LOGIC ---
    if straight_dy_needed < 0:
        straight_dy_needed = 0.0
    
    # Calculate straight length
    theta_rad = np.radians(angle)
    straight_length = straight_dy_needed / np.sin(theta_rad)
    
    # E. Stitch the S-Bend
    c = gf.Component()
    
    # 1. Bend Up
    b1 = c << bend_c
    
    # 2. Straight
    current_port = b1.ports["o2" if "o2" in b1.ports else "2"]
    
    if straight_length > 0.001:
        straight_c = gf.components.straight(length=straight_length, cross_section=cross_section)
        s1 = c << straight_c
        b1_out_name = "o2" if "o2" in b1.ports else "2"
        s1.connect("o1", b1.ports[b1_out_name])
        current_port = s1.ports["o2"]

    # 3. Bend Down (Mirror Y)
    b2 = c << bend_c
    b2.mirror_y()
    b2_in_name = "o1" if "o1" in b2.ports else "1"
    b2.connect(b2_in_name, current_port)
    
    c.add_port("o1", port=b1.ports["o1" if "o1" in b1.ports else "1"])
    c.add_port("o2", port=b2.ports["o2" if "o2" in b2.ports else "2"])
    return c


@gf.cell
def tunable_beam_splitter(
    wg_width: float = 1.2,
    coupler_length: float = 255.0,
    coupler_gap: float = 1.0,
    mzi_arm_length: float = 3400.0,
    arm_spacing: float = 40.0,
    bend_radius: float = 210.0, 
    bend_angle: float = 20.0,
    bend_p: float = 0.5,
) -> gf.Component:
    
    c = gf.Component()
    xs = gf.cross_section.strip(width=wg_width)

    # --- GEOMETRY CALCULATION ---
    delta_y = arm_spacing - (coupler_gap + wg_width)

    # 1. Generate the master S-Bend
    s_bend_up = create_precise_euler_sbend(xs, bend_radius, bend_angle, bend_p, delta_y)
    
    # Get length for the bottom straights
    sbend_len = s_bend_up.xmax - s_bend_up.xmin
    
    # --- ASSEMBLY SEQUENCE (Left to Right) ---
    
    # 1. INPUT BOTTOM (Straight)
    # This is the anchor at (0,0)
    in_bot = c << gf.components.straight(length=sbend_len, cross_section=xs)
    in_bot.x = 0; in_bot.y = 0
    
    # 2. COUPLER 1 (Splitter)
    # Connect its bottom-input (o1) to the input straight
    cp1 = c << gf.components.coupler(gap=coupler_gap, length=coupler_length, cross_section=xs)
    cp1.connect("o1", in_bot.ports["o2"])
    
    # 3. INPUT TOP (Fan-In)
    # This connects to the Top-Input of the coupler (o2)
    # The S-Bend component goes Low->High. 
    # To act as a Fan-In (High->Low), we Mirror Y.
    # Note: Mirror Y makes it go from (0,0) down to (L, -H).
    # If we connect its "end" (o2) to the coupler's input (o2), it will extend backwards correctly.
    in_top = c << s_bend_up
    in_top.mirror_y()
    # Connect the OUTPUT (o2) of the fan-in to the INPUT (o2) of the coupler
    in_top.connect("o2", cp1.ports["o2"])
    
    # 4. MZI ARMS
    
    # Top Arm: Bend Up -> Straight -> Bend Down
    # We expand FROM the coupler output (o3)
    bend_expand = c << s_bend_up
    bend_expand.connect("o1", cp1.ports["o3"]) 
    
    arm_top = c << gf.components.straight(length=mzi_arm_length, cross_section=xs)
    arm_top.connect("o1", bend_expand.ports["o2"])
    
    # Contract: Connect START (o1) of mirrored bend to end of arm
    bend_contract = c << s_bend_up
    bend_contract.mirror_x() # Contract is reverse of expand
    bend_contract.connect("o2", arm_top.ports["o2"])
    
    # Bot Arm: Long Straight
    bot_mzi_len = (2 * sbend_len) + mzi_arm_length
    arm_bot = c << gf.components.straight(length=bot_mzi_len, cross_section=xs)
    arm_bot.connect("o1", cp1.ports["o4"])
    
    # 5. COUPLER 2 (Combiner)
    cp2 = c << gf.components.coupler(gap=coupler_gap, length=coupler_length, cross_section=xs)
    cp2.connect("o1", arm_bot.ports["o2"]) # Connect to Bottom Arm
    
    # 6. OUTPUTS
    
    # Bot Output: Straight
    out_bot = c << gf.components.straight(length=sbend_len, cross_section=xs)
    out_bot.connect("o1", cp2.ports["o4"])
    
    # Top Output: Fan-Out (Bend Up)
    out_top = c << s_bend_up
    out_top.connect("o1", cp2.ports["o3"])
    
    # --- PORTS ---
    c.add_port("o1", port=in_bot.ports["o1"])   # Input Bot
    c.add_port("o2", port=in_top.ports["o1"])   # Input Top (The start of the fan-in)
    c.add_port("o3", port=out_bot.ports["o2"])  # Output Bot
    c.add_port("o4", port=out_top.ports["o2"])  # Output Top
    
    return c

if __name__ == "__main__":
    c = tunable_beam_splitter()
    c.show()
    print("✅ Full Asymmetric TBS Generated")