# vision/reference_library.py
"""
Reference library of few-shot examples for the vision model.
These examples represent the "Gold Standard" for handling loops, terminations, and basic connections.
"""

EXAMPLES = [
    {
        "name": "Simple Ring Resonator Connection",
        "description": "A simple ring resonator connected to a single feed waveguide with grating couplers on each side.",
        "yaml": """
instances:
  grating_coupler_1:
    component: grating_coupler
    settings: {}
  grating_coupler_2:
    component: grating_coupler
    settings: {}
  ring_1:
    component: ring_resonator
    settings: {}
  terminator_1:
    component: terminator
    settings: {}
  terminator_2:
    component: terminator
    settings: {}

placements:
  grating_coupler_1:
    x: "C2_C"
    y: "C2_C"
    rotation: 0
  grating_coupler_2:
    x: "C4_C"
    y: "C4_C"
    rotation: 180
  ring_1:
    x: "C3_C"
    y: "C3_C"
    rotation: 0
  terminator_1:
    x: "C3_NW"
    y: "C3_NW"
    rotation: 0
  terminator_2:
    x: "C3_NE"
    y: "C3_NE"
    rotation: 0

routes:
  route_1:
    links:
      grating_coupler_1,o1: ring_1,o1
  route_2:
    links:
      ring_1,o3: grating_coupler_2,o1
  route_3:
    links:
      ring_1,o4: terminator_2,o1
  route_4:
    links:
      ring_1,o2: terminator_1,o1
"""
    },
    {
        "name": "The Loopback (Self-Reference)",
        "description": "CRITICAL: An MZI where output ports o3 and o4 connect to EACH OTHER via a bend.",
        "yaml": """
instances:
  mzi_loop:
    component: mzi_no_heater
    settings: {}
  loop_bend:
    component: euler_bend
    settings: {}
  terminator_1:
    component: terminator
    settings: {}
  terminator_2:
    component: terminator
    settings: {}

placements:
  mzi_loop:
    x: "B5_W"
    y: "B5_W"
    rotation: 0
  loop_bend:
    x: "B5_E"
    y: "B5_E"
    rotation: 0
  terminator_1:
    x: "B5_NW"
    y: "B5_NW"
    rotation: 0
  terminator_2:
    x: "B5_SW"
    y: "B5_SW"
    rotation: 0

routes:
  # Bridging the same component's ports with a bend
  route_top:
    links:
      mzi_loop,o4: loop_bend,o1
  route_btm:
    links:
      loop_bend,o2: mzi_loop,o3
  route_unused_input:
    links:
      mzi_loop,o2: terminator_1,o1
  route_unused_output:
    links:
      mzi_loop,o1: terminator_2,o1
"""
    }
]
