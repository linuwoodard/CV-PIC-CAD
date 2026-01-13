import os
import gdsfactory as gf
from pdk import tapered_input_coupler

print(f"1. PDK imported successfully.")

# 1. Create the component with exaggerated values so features are obvious
c = tapered_input_coupler(
    taperLength=200.0,      # Length of the trapezoid part
    dicingClearance=100.0,  # Length of the straight "tab" part
    taperWidth=0.5,         # Narrow tip width
    wgWidth=2.0             # Wide base width
)

# 2. Print success message
print("✅ Taper created successfully.")
print(f"Total Expected Length: {200 + 100} um")


# Write the file
gds_path = "test_output.gds"
c.write_gds(gds_path)

print(f"3. SUCCESS! Saved GDS file to: {os.path.abspath(gds_path)}")

# 3. Show in KLayout
c.show()