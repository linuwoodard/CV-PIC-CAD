import gdsfactory as gf
from pdk import racetrack_resonator

print("Generating Racetrack Resonator...")

# Build with defaults
c = racetrack_resonator()

# Save
c.write_gds("test_racetrack.gds")
c.show()

print("✅ Racetrack Generated.")
print("   Check: Couplers should be shifted to the RIGHT side of the straights.")