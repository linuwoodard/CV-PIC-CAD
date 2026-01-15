import gdsfactory as gf
from pathlib import Path
from pdk import focusing_grating_coupler

def test_gc():
    # 1. Setup Output
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "gdsOutputs"
    output_dir.mkdir(exist_ok=True)

    c = gf.Component("GC_Test_Array")

    # 2. Add Grating Coupler 1
    gc1 = c << focusing_grating_coupler(
        pitch=1.16,
        defocus=-8.0,
        duty_cycle_start=0.8,
        duty_cycle_end=0.42,
        wg_width=1.2,
        grating_width=20.0
    )
    gc1.x = 0
    gc1.y = 0

    # 3. Add Grating Coupler 2 (flipped)
    gc2 = c << focusing_grating_coupler()
    gc2.mirror_x()
    gc2.x = 200
    gc2.y = 0
    
    # 4. Connect them
    # FIX: Pass 'c' as the first argument. 
    # In GDSFactory v8+, route_single adds the route directly to 'c'.
    gf.routing.route_single(
        c,                              # <--- Component required here
        gc1.ports["o1"], 
        gc2.ports["o1"],
        cross_section=gf.cross_section.strip(width=1.2)
    )
    
    # Note: We do NOT need 'c.add(route.references)' anymore.

    # 5. Save and Show
    gds_path = output_dir / "grating_coupler_test.gds"
    c.write_gds(gds_path)
    print(f"[SUCCESS] GDS saved to: {gds_path}")
    c.show()

if __name__ == "__main__":
    test_gc()