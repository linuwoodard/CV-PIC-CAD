import gdsfactory as gf
from pdk import euler_bend

# Create the component
c = euler_bend(radius=210, angle=20, p=0.5, width=1.2)

# Show it
c.show() 

# Quick print to confirm size
# Height should be roughly 12-13um (NOT 18,000um)
print(f"Bend Height: {c.ysize:.3f} um")



