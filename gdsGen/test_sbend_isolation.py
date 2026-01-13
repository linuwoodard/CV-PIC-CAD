import gdsfactory as gf
import numpy as np

def create_precise_euler_bend(cross_section, radius, angle, p):
    """
    Creates a single Euler bend using path extrusion to guarantee strict geometry.
    """
    P = gf.Path()
    P.append(gf.path.euler(radius=radius, angle=angle, p=p))
    c = P.extrude(cross_section)
    
    # Map ports cleanly
    if 'o1' not in c.ports:
        c.add_port('o1', port=c.ports['1'])
        c.add_port('o2', port=c.ports['2'])
    return c

def test_sbend_construction():
    # --- Parameters ---
    wg_width = 1.2
    radius = 210.0
    angle = 20.0  # Degrees
    p = 0.5
    
    # Target total height (e.g., the shift needed for 40um spacing)
    # If gap=1um, width=1.2um, arm_spacing=40um
    # shift = 40 - (1 + 1.2) = 37.8 um
    target_height = 37.8 

    # --- 1. Build Single Bend & Measure ---
    xs = gf.cross_section.strip(width=wg_width)
    bend = create_precise_euler_bend(xs, radius, angle, p)
    
    p1 = bend.ports['o1'].center
    p2 = bend.ports['o2'].center
    bend_dy = abs(p2[1] - p1[1])
    
    print(f"--- GEOMETRY CHECK ---")
    print(f"Bend Radius: {radius} um")
    print(f"Bend Angle:  {angle} degrees")
    print(f"Calculated Bend Height (dy): {bend_dy:.4f} um")
    
    # Expected Math: R * (1 - cos(theta))
    # Note: For Euler with p=0.5, the effective height is slightly different than a circular arc,
    # but it should be close.
    
    # --- 2. Calculate Straight Section ---
    straight_dy_needed = target_height - (2 * bend_dy)
    print(f"Target Total Height:       {target_height:.4f} um")
    print(f"Height remaining for Straight: {straight_dy_needed:.4f} um")
    
    if straight_dy_needed < 0:
        print("❌ ERROR: Bends are too tall for this target height!")
        return

    theta_rad = np.radians(angle)
    straight_length = straight_dy_needed / np.sin(theta_rad)
    
    straight = gf.components.straight(length=straight_length, cross_section=xs)

    # --- 3. Assemble S-Bend ---
    c = gf.Component("Isolated_SBend")
    
    # A. Bend Up (+Angle)
    b1 = c << bend
    
    # B. Straight (Angled)
    s1 = c << straight
    s1.connect("o1", b1.ports["o2"])
    
    # C. Bend Down (-Angle)
    # To get the opposite angle, we mirror the original bend.
    # Original bends 'Left' (positive angle). Mirrored Y bends 'Right' (negative angle).
    b2 = c << bend
    b2.mirror_y() 
    b2.connect("o1", s1.ports["o2"])
    
    c.show()
    print("✅ S-Bend created. Check KLayout.")

if __name__ == "__main__":
    test_sbend_construction()