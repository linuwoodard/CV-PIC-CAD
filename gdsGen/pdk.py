import gdsfactory as gf
from functools import partial

# --- 1. Tapered Input Coupler (Constructed Geometry) ---


@gf.cell
def tapered_input_coupler(
    taperLength: float = 200.0,
    taperWidth: float = 0.5,
    wgWidth: float = 1.2,
    dicingClearance: float = 50.0,
    isTab: bool = True,  # Toggle the dicing anchor tab
    **kwargs
) -> gf.Component:
    """
    Creates an input coupler with an optional dicing anchor 'tab'.
    
    Structure (Left to Right):
    [Tab Straight (5um)] -> [Tab Taper (5->0.5)] -> [Dicing Clearance] -> [Main Taper (0.5->1.2)]
    """
    c = gf.Component()

    # --- 1. Define Standard Parts ---
    # The normal dicing clearance (narrow tip)
    dicing_straight = gf.components.straight(
        length=dicingClearance, 
        width=taperWidth
    )
    
    # The main adiabatic taper (narrow -> wide)
    main_taper = gf.components.taper(
        length=taperLength, 
        width1=taperWidth, 
        width2=wgWidth
    )

    # --- 2. Place Standard Parts ---
    ref_dicing = c << dicing_straight
    ref_main = c << main_taper
    
    # Connect: Dicing (o2) -> Main Taper (o1)
    ref_main.connect("o1", ref_dicing.ports["o2"])

    # --- 3. Optional Tab Logic ---
    if isTab:
        # Tab Parameters (Hardcoded per request)
        tab_width = 5.0
        tab_len = 5.0
        tab_taper_len = 5.0
        
        # Create Tab Components
        # Taper DOWN from Tab (5.0) to Tip (taperWidth)
        tab_taper = gf.components.taper(
            length=tab_taper_len,
            width1=tab_width,
            width2=taperWidth
        )
        # Wide Straight Section at the very edge
        tab_straight = gf.components.straight(
            length=tab_len,
            width=tab_width
        )
        
        # Place Tab Components
        ref_tab_taper = c << tab_taper
        ref_tab_straight = c << tab_straight
        
        # Connect: Tab Taper (o2=narrow) -> Dicing Straight (o1)
        ref_tab_taper.connect("o2", ref_dicing.ports["o1"])
        
        # Connect: Tab Straight (o2) -> Tab Taper (o1=wide)
        ref_tab_straight.connect("o2", ref_tab_taper.ports["o1"])
        
        # Expose Input Port (from the wide tab edge)
        c.add_port("o1", port=ref_tab_straight.ports["o1"])
        
    else:
        # No Tab: Expose the narrow dicing straight directly
        c.add_port("o1", port=ref_dicing.ports["o1"])

    # --- 4. Expose Output Port ---
    c.add_port("o2", port=ref_main.ports["o2"])
    
    # Housekeeping
    c.copy_child_info(main_taper)
    
    return c


# --- 2. MZI Heater (Configured Wrapper) ---
import gdsfactory as gf
import numpy as np

# --- Helper for Tunable Beam Splitter ---
def _create_precise_euler_sbend(cross_section, radius, angle, p, dy_target):
    """
    Internal helper for tunable_beam_splitter.
    Constructs an Euler S-Bend using Path extrusions with unit-scaling fixes.
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
    
    # Handle DBU scaling (nanometers vs microns)
    dbu = 0.001 if raw_dy > 500 else 1.0
    bend_height = raw_dy * dbu
    
    # D. Calculate Straight Section
    min_required_height = 2 * bend_height
    straight_dy_needed = dy_target - min_required_height
    
    # Auto-Fix Logic: Snap to minimum height if gap is slightly too tight
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
    """
    Asymmetric Tunable Beam Splitter (MZI) with separated input/output ports.
    - One arm is straight (bottom).
    - One arm bends (top).
    - Includes input/output fan-out to ensure ports are separated by 'arm_spacing'.
    """
    
    c = gf.Component()
    xs = gf.cross_section.strip(width=wg_width)

    # --- GEOMETRY CALCULATION ---
    delta_y = arm_spacing - (coupler_gap + wg_width)

    # 1. Generate the master S-Bend
    s_bend_up = _create_precise_euler_sbend(xs, bend_radius, bend_angle, bend_p, delta_y)
    
    # Get length for the bottom straights
    sbend_len = s_bend_up.xmax - s_bend_up.xmin
    
    # --- ASSEMBLY SEQUENCE (Left to Right) ---
    
    # 1. INPUT BOTTOM (Straight)
    in_bot = c << gf.components.straight(length=sbend_len, cross_section=xs)
    in_bot.x = 0; in_bot.y = 0
    
    # 2. COUPLER 1 (Splitter)
    cp1 = c << gf.components.coupler(gap=coupler_gap, length=coupler_length, cross_section=xs)
    cp1.connect("o1", in_bot.ports["o2"])
    
    # 3. INPUT TOP (Fan-In)
    in_top = c << s_bend_up
    in_top.mirror_y()
    in_top.connect("o2", cp1.ports["o2"])
    
    # 4. MZI ARMS
    # Top Arm: Bend Up -> Straight -> Bend Down
    bend_expand = c << s_bend_up
    bend_expand.connect("o1", cp1.ports["o3"]) 
    
    arm_top = c << gf.components.straight(length=mzi_arm_length, cross_section=xs)
    arm_top.connect("o1", bend_expand.ports["o2"])
    
    bend_contract = c << s_bend_up
    bend_contract.mirror_x()
    bend_contract.connect("o2", arm_top.ports["o2"])
    
    # Bot Arm: Long Straight
    bot_mzi_len = (2 * sbend_len) + mzi_arm_length
    arm_bot = c << gf.components.straight(length=bot_mzi_len, cross_section=xs)
    arm_bot.connect("o1", cp1.ports["o4"])
    
    # 5. COUPLER 2 (Combiner)
    cp2 = c << gf.components.coupler(gap=coupler_gap, length=coupler_length, cross_section=xs)
    cp2.connect("o1", arm_bot.ports["o2"])
    
    # 6. OUTPUTS
    # Bot Output
    out_bot = c << gf.components.straight(length=sbend_len, cross_section=xs)
    out_bot.connect("o1", cp2.ports["o4"])
    
    # Top Output
    out_top = c << s_bend_up
    out_top.connect("o1", cp2.ports["o3"])
    
    # --- PORTS ---
    c.add_port("o1", port=in_bot.ports["o1"])   # Input Bot
    c.add_port("o2", port=in_top.ports["o1"])   # Input Top
    c.add_port("o3", port=out_bot.ports["o2"])  # Output Bot
    c.add_port("o4", port=out_top.ports["o2"])  # Output Top
    
    return c