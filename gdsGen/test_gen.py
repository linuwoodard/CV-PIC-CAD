import gdsfactory as gf
import os

# SKIP the version print. It's not needed.

print("1. GDSFactory imported successfully.")

# Create a component
c = gf.components.mzi()
print("2. Component created.")

# Write the file
gds_path = "test_output.gds"
c.write_gds(gds_path)

print(f"3. SUCCESS! Saved GDS file to: {os.path.abspath(gds_path)}")