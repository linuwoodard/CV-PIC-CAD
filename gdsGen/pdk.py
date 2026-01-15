import gdsfactory as gf
import numpy as np
from functools import partial

# --- 1. Tapered Input Coupler ---
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


# --- Helper for S-Bends ---
def _create_precise_euler_sbend(cross_section, radius, angle, p, dy_target):
    """
    Internal helper for mzi_no_heater and racetrack_resonator.
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


# --- 2. MZI No Heater (Formerly tunable_beam_splitter) ---
@gf.cell
def mzi_no_heater(
    wg_width: float = 1.2,
    coupler_length: float = 255.0,
    coupler_gap: float = 1.0,
    mzi_arm_length: float = 3400.0,
    arm_spacing: float = 40.0,
    bend_radius: float = 210.0, 
    bend_angle: float = 20.0,
    bend_p: float = 0.5,
    **kwargs
) -> gf.Component:
    """
    Asymmetric MZI without heaters.
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


# --- 3. Euler Bend ---
@gf.cell
def euler_bend(
    radius: float = 210.0,
    angle: float = 20.0,
    p: float = 0.5,
    width: float = 1.2,
    **kwargs
) -> gf.Component:
    """
    A standalone Euler bend with strict geometric control.
    Uses gf.path to ensure exact p-factor and radius compliance, 
    bypassing potential bounding-box issues in standard components.
    
    Args:
        radius: Effective radius of the bend (um)
        angle: Total turn angle (degrees)
        p: Euler spiral parameter (0 = circular, 0.5 = euler, 1.0 = heavy smoothing)
        width: Waveguide width (um)
    """
    c = gf.Component()
    
    # 1. Define the exact geometric path
    # use_eff=False ensures 'radius' is treated as the minimum bend radius R_min
    path = gf.path.euler(radius=radius, angle=angle, p=p, use_eff=False)
    
    # 2. Define Cross Section
    xs = gf.cross_section.strip(width=width)
    
    # 3. Extrude
    ref = c << path.extrude(xs)
    
    # 4. Port Management
    # Path extrusion usually names ports '1' and '2'. We map them to standard 'o1'/'o2'.
    # We check keys safely to handle different GDSFactory versions.
    
    p1_name = "1" if "1" in ref.ports else "o1"
    p2_name = "2" if "2" in ref.ports else "o2"
    
    c.add_port("o1", port=ref.ports[p1_name])
    c.add_port("o2", port=ref.ports[p2_name])
    
    # copy info helps with layer propagation
    c.info['radius'] = radius
    c.info['angle'] = angle
    
    return c


# --- 4. Racetrack Resonator ---
@gf.cell
def racetrack_resonator(
    straightLength: float = 12000.0,
    rtBendRadius: float = 210.0,
    rtEulerP: float = 0.5,
    couplingGap: float = 1.0,
    couplingLength: float = 600.0,
    bendAngle: float = 20.0,
    couplerEulerP: float = 0.5,
    wgSpacing: float = 30.0,
    wgWidth: float = 1.2,
    **kwargs
) -> gf.Component:
    """
    Racetrack Resonator with Euler bends.
    """
    c = gf.Component()
    xs = gf.cross_section.strip(width=wgWidth)

    # --- 1. The Racetrack Loop ---
    
    # Straights (Top and Bot)
    # We use standard components to guarantee 1:1 scaling (12000um = 12000um)
    rt_straight = gf.components.straight(length=straightLength, cross_section=xs)
    
    # Bends (180 deg)
    # We use path.euler to ensure it doesn't explode
    p_180 = gf.path.euler(radius=rtBendRadius, angle=180, p=rtEulerP, use_eff=False)
    bend180 = p_180.extrude(xs)
    
    # Place Loop
    # Top Straight
    rt_top = c << rt_straight
    rt_top.x = 0; rt_top.y = 0
    
    # Right Bend (Clockwise/Down)
    bend_r = c << bend180
    bend_r.mirror_y() # Standard goes Up, we need Down
    bend_r.connect("o1", rt_top.ports["o2"])
    
    # Bot Straight
    rt_bot = c << rt_straight
    rt_bot.connect("o1", bend_r.ports["o2"])
    
    # Left Bend (Clockwise/Up)
    bend_l = c << bend180
    bend_l.mirror_y()
    bend_l.connect("o1", rt_bot.ports["o2"])
    
    # --- 2. Bus Couplers ---
    
    # Helper for Bus S-Bends (reusing your safe logic)
    delta_y = wgSpacing
    # NOTE: Ensure _create_precise_euler_sbend is available in your PDK
    sbend = _create_precise_euler_sbend(xs, rtBendRadius, bendAngle, couplerEulerP, delta_y)
    
    c_straight = gf.components.straight(length=couplingLength, cross_section=xs)
    pitch = wgWidth + couplingGap
    
    # -- Top Bus --
    top_c = c << c_straight
    top_c.xmax = rt_top.xmax
    top_c.ymin = rt_top.ymax + couplingGap
    
    # Fan-In/Out
    t_in = c << sbend
    t_in.mirror_y()
    t_in.connect("o2", top_c.ports["o1"])
    
    t_out = c << sbend
    t_out.connect("o1", top_c.ports["o2"])
    
    # -- Bot Bus --
    bot_c = c << c_straight
    bot_c.xmax = rt_bot.xmax # Right aligned
    bot_c.ymax = rt_bot.ymin - couplingGap
    
    # Fan-In/Out
    b_in = c << sbend
    b_in.connect("o2", bot_c.ports["o1"])
    
    b_out = c << sbend
    b_out.mirror_y()
    b_out.connect("o1", bot_c.ports["o2"])
    
    # Ports
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=t_out.ports["o2"])
    c.add_port("o3", port=b_in.ports["o1"])
    c.add_port("o4", port=b_out.ports["o2"])
    
    return c

@gf.cell
def ring_resonator(
    radius: float = 200.0,
    isDoubleSided: bool = True,
    couplingGap: float = 1.0,
    wgWidth: float = 1.2,
    ringWgWidth: float = 1.2,
    **kwargs
) -> gf.Component:
    """
    A simple Ring Resonator with straight bus waveguides.
    
    Args:
        radius: Radius of the ring (center to center of waveguide).
        isDoubleSided: If True, adds a top drop port. If False, only creates bottom bus.
        couplingGap: Gap between the ring and the bus waveguides.
        wgWidth: Width of the straight bus waveguides.
        ringWgWidth: Width of the ring waveguide.
    """
    c = gf.Component()
    
    # Define Cross Sections
    xs_bus = gf.cross_section.strip(width=wgWidth)
    xs_ring = gf.cross_section.strip(width=ringWgWidth)
    
    # 1. Create the Ring
    # FIX: Use gf.path.euler with p=0 (circular) to generate the loop.
    # angle=360 makes a full circle. 
    # use_eff=False ensures 'radius' is the physical radius.
    path_ring = gf.path.euler(radius=radius, angle=360, p=0, use_eff=False)
    
    ring = c << path_ring.extrude(xs_ring)
    
    # Center the ring at (0,0)
    # The path generates off-center (starting at 0,0), so we force 
    # the center of the component's bounding box to (0,0).
    ring.x = 0
    ring.y = 0
    
    # 2. Geometry Calculations
    # Bus Y position = +/- (Radius + Gap + (RingWidth/2) + (BusWidth/2))
    # We measure from center (0,0).
    bus_offset = radius + (ringWgWidth / 2) + couplingGap + (wgWidth / 2)
    
    bus_length = (2 * radius) + 100.0 # Make bus slightly longer than the ring
    
    # 3. Bottom Bus (Always present)
    bus_bot = c << gf.components.straight(length=bus_length, cross_section=xs_bus)
    bus_bot.x = 0
    bus_bot.y = -bus_offset
    
    c.add_port("o1", port=bus_bot.ports["o1"]) # Input (West)
    c.add_port("o2", port=bus_bot.ports["o2"]) # Through (East)
    
    # 4. Top Bus (Conditional)
    if isDoubleSided:
        bus_top = c << gf.components.straight(length=bus_length, cross_section=xs_bus)
        bus_top.x = 0
        bus_top.y = bus_offset
        
        c.add_port("o3", port=bus_top.ports["o2"]) # Drop (East)
        c.add_port("o4", port=bus_top.ports["o1"]) # Add (West)
        
    else:
        # Create Phantom Ports
        # These allow routers to see ports even if the geometry isn't there.
        
        # Port o4 (Top West)
        c.add_port(
            name="o4",
            center=(-bus_length/2, bus_offset),
            width=wgWidth,
            orientation=180,
            layer=xs_bus.layer
        )
        
        # Port o3 (Top East)
        c.add_port(
            name="o3",
            center=(bus_length/2, bus_offset),
            width=wgWidth,
            orientation=0,
            layer=xs_bus.layer
        )

    return c

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

@gf.cell
def focusing_grating_coupler(
    pitch: float = 1.16,
    n_periods: int = 30,
    duty_cycle_start: float = 0.8,
    duty_cycle_end: float = 0.42,
    wg_width: float = 1.2,
    taper_width: float = 1.0,
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
    """
    c = gf.Component()

    # 1. Derived Parameters
    neff = lambda0/pitch + np.sin(np.radians(theta_deg))
    q_min = round(focusing_length * (neff - np.sin(np.radians(theta_deg))) / lambda0)
    duty_cycles = np.linspace(duty_cycle_start, duty_cycle_end, n_periods)

    # 2. Generate Fanout Body Points (Trapezoid)
    total_grating_len = pitch * n_periods
    L_total = focusing_length + defocus + total_grating_len
    
    fanout_pts = [
        (0, -taper_width/2),
        (L_total, -grating_width/2),
        (L_total, grating_width/2),
        (0, taper_width/2)
    ]
    
    # 3. Generate Hole Points
    holes_polygons = []
    
    curr_x = 0
    small_buffer = 1.5
    hole_origin_x = focusing_length + defocus - small_buffer
    
    for i in range(n_periods):
        dc = duty_cycles[i]
        w_hole = (1.0 - dc) * pitch
        q = q_min + (i + 1)
        raw_pts = _gen_focusing_stripe(q, neff, theta_deg, w_hole, theta_opening_deg, lambda0)
        
        shift_x = hole_origin_x + curr_x + pitch
        translated_pts = [(x + shift_x, y) for x, y in raw_pts]
        holes_polygons.append(translated_pts)
        curr_x += pitch

    # 4. Boolean Subtraction
    c_body = gf.Component()
    c_body.add_polygon(fanout_pts, layer=layer)
    
    c_holes = gf.Component()
    for pts in holes_polygons:
        c_holes.add_polygon(pts, layer=layer)
        
    bool_component = gf.boolean(A=c_body, B=c_holes, operation="not", layer=layer)
    c.add_ref(bool_component)

    # 5. Input Taper (Geometric placement)
    wg_max_len = 100.0
    input_taper_len = max(10.0, wg_max_len - L_total)
    
    # We define width1 as TAPER_WIDTH (Wide) and width2 as WG_WIDTH (Narrow)
    # Default taper: o1=width1 @ (0,0), o2=width2 @ (length,0)
    taper = gf.components.taper(
        length=input_taper_len,
        width1=taper_width,  # Wide end (at grating interface)
        width2=wg_width,     # Narrow end (input)
        layer=layer
    )
    t_ref = c << taper
    
    # Mirror X: 
    # o1 (Wide) stays at (0,0) (Correct, touches fanout)
    # o2 (Narrow) moves to (-length, 0) (Correct, becomes input)
    t_ref.mirror_x()
    
    # 6. Expose Port
    # t_ref.ports["o2"] is the narrow end at x = -length
    c.add_port("o1", port=t_ref.ports["o2"])

    return c