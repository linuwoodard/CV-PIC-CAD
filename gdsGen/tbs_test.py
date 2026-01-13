print("0. Initializing GDSFactory...")
import os
import gdsfactory as gf

# Import your component
try:
    from tunable_beam_splitter import tunable_beam_splitter
except ImportError:
    print("❌ Error: Could not find 'tunable_beam_splitter.py'.")
    exit()

print("1. Library loaded. Generating Tunable Beam Splitter...")

# 1. Create the component with the NEW working parameters
c = tunable_beam_splitter(
    wg_width=1.2,
    coupler_length=255.0,
    coupler_gap=1.0,
    mzi_arm_length=3400.0,
    
    # --- THESE ARE THE CRITICAL UPDATES ---
    arm_spacing=40.0,    # Increased space
    bend_radius=210.0,   # Large radius
    bend_angle=20.0      # Reduced angle so it fits vertically
)

print("2. Component generated successfully.")

# 2. Validation Check
y_bot = c.ports["o1"].center[1]
y_top = c.ports["o2"].center[1]
input_spacing = abs(y_top - y_bot)

print(f"   --- Measurements ---")
print(f"   Input Port Spacing:  {input_spacing:.3f} um")
print(f"   MZI Arm Spacing:     40.0 um")

# 3. Save and Show
gds_path = "test_tbs.gds"
c.write_gds(gds_path)

print(f"3. SUCCESS! Saved to: {os.path.abspath(gds_path)}")
c.show()