import gdsfactory as gf
from pdk import tunable_beam_splitter

# Attempt to build from PDK
c = tunable_beam_splitter()
c.show()
print("✅ Successfully built Tunable Beam Splitter from PDK!")