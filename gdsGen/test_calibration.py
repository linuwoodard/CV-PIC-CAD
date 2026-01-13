import gdsfactory as gf
import os

def test_units():
    print("0. Starting Unit Calibration...")
    
    # Create a blank component
    c = gf.Component("Unit_Calibration")
    
    # 1. Draw a Simple Rectangle (100um x 10um)
    # If units are correct, this should be 100um wide.
    # If units are wrong (1000x), this will be 100mm (10cm) wide!
    ref_rect = c << gf.components.rectangle(size=(100.0, 10.0), layer=(1,0))
    ref_rect.x = 0
    ref_rect.y = 0
    
    # 2. Draw your S-Bend (Just one)
    # We use a standard circular bend first to rule out Euler math errors.
    # If this is 1000x too big, we know it's a global unit setting, not the Euler math.
    bend = gf.components.bend_circular(radius=210.0, angle=20.0, width=1.2)
    ref_bend = c << bend
    ref_bend.xmin = 0
    ref_bend.ymin = 20 # Place it above the rectangle
    
    # 3. Check Internal Database Units (DBU)
    # Standard is 0.001 (1nm precision for 1um units)
    print(f"   Internal DBU (Database Unit): {c.kcl.dbu}")
    
    # 4. Save
    gds_path = "calibration_test.gds"
    c.write_gds(gds_path)
    
    print(f"1. Saved calibration to: {os.path.abspath(gds_path)}")
    print("   --> PLEASE MEASURE THE RECTANGLE IN KLAYOUT.")
    print("   --> Is it 100 um or 100,000 um (100 mm)?")
    
    c.show()

if __name__ == "__main__":
    test_units()