# vision/reference_library.py
"""
Reference library of few-shot examples for the vision model.
These examples represent the "Gold Standard" for handling loops, terminations, and basic connections.
"""

EXAMPLES = [
    {
        "name": "MZI with Perfect Alignment (Functional Example)",
        "description": "A complete MZI circuit with tapered input couplers using proper relative placement syntax. MZI is anchored at (0,0), all tapers use 'to:' syntax for relative placement. All routes properly connect ports.",
        "yaml": """
name: mzi_perfect_alignment

instances:
  mzi_1:
    component: mzi_no_heater
    settings: 
      arm_spacing: 40.0

  tapered_input_coupler_1: # TL (Top Left)
    component: tapered_input_coupler
    settings: {}
  
  tapered_input_coupler_2: # BL (Bottom Left)
    component: tapered_input_coupler
    settings: {}

  tapered_input_coupler_3: # BR (Bottom Right)
    component: tapered_input_coupler
    settings: {}

  tapered_input_coupler_4: # TR (Top Right)
    component: tapered_input_coupler
    settings: {}

placements:
  # ANCHOR: MZI at absolute position (0, 0)
  mzi_1:
    x: 0
    y: 0
    rotation: 0

  # RELATIVE: Tapers connect to MZI ports with offsets
  # --- LEFT SIDE (Inputs) ---
  tapered_input_coupler_1: # Top Left
    to: mzi_1,o2
    port: o2
    dx: 0
    dy: 0
    rotation: 0

  tapered_input_coupler_2: # Bottom Left
    to: mzi_1,o1
    port: o2
    dx: 0
    dy: 0
    rotation: 0

  # --- RIGHT SIDE (Outputs) ---
  tapered_input_coupler_3: # Bottom Right
    to: mzi_1,o3
    port: o2
    dx: 0
    dy: 0
    rotation: 0

  tapered_input_coupler_4: # Top Right
    to: mzi_1,o4
    port: o2
    dx: 0
    dy: 0
    rotation: 0

routes:
  route_1_TL:
    links:
      tapered_input_coupler_1,o2: mzi_1,o2
    settings:
      cross_section: strip_1p2

  route_2_BL:
    links:
      tapered_input_coupler_2,o2: mzi_1,o1
    settings:
      cross_section: strip_1p2

  route_3_BR:
    links:
      mzi_1,o3: tapered_input_coupler_3,o2
    settings:
      cross_section: strip_1p2

  route_4_TR:
    links:
      mzi_1,o4: tapered_input_coupler_4,o2
    settings:
      cross_section: strip_1p2
"""
    },
    {
        "name": "MZI with 90 degree rotation (Functional Example) ",
        "description": "A complete MZI circuit with tapered input couplers using proper relative placement syntax. MZI is anchored at (0,0), all tapers use 'to:' syntax for relative placement. All routes properly connect ports. MZI is rotated 90 degrees.",
        "yaml": """
name: mzi_90_degree_rotation

instances:
  mzi_1:
    component: mzi_no_heater
    settings: 
      arm_spacing: 40.0

  tapered_input_coupler_1: # TL (Top Left)
    component: tapered_input_coupler
    settings: {}
  
  tapered_input_coupler_2: # BL (Bottom Left)
    component: tapered_input_coupler
    settings: {}

  tapered_input_coupler_3: # BR (Bottom Right)
    component: tapered_input_coupler
    settings: {}

  tapered_input_coupler_4: # TR (Top Right)
    component: tapered_input_coupler
    settings: {}

placements:
  # ANCHOR: MZI at absolute position (0, 0)
  mzi_1:
    x: 0
    y: 0
    rotation: 90

  # RELATIVE: Tapers connect to MZI ports with offsets
  # --- LEFT SIDE (Inputs) ---
  tapered_input_coupler_1: # Top Left
    to: mzi_1,o2
    port: o2
    dx: 0
    dy: 0
    rotation: 0

  tapered_input_coupler_2: # Bottom Left
    to: mzi_1,o1
    port: o2
    dx: 0
    dy: 0
    rotation: 0

  # --- RIGHT SIDE (Outputs) ---
  tapered_input_coupler_3: # Bottom Right
    to: mzi_1,o3
    port: o2
    dx: 0
    dy: 0
    rotation: 0

  tapered_input_coupler_4: # Top Right
    to: mzi_1,o4
    port: o2
    dx: 0
    dy: 0
    rotation: 0

routes:
  route_1_TL:
    links:
      tapered_input_coupler_1,o2: mzi_1,o2
    settings:
      cross_section: strip_1p2

  route_2_BL:
    links:
      tapered_input_coupler_2,o2: mzi_1,o1
    settings:
      cross_section: strip_1p2

  route_3_BR:
    links:
      mzi_1,o3: tapered_input_coupler_3,o2
    settings:
      cross_section: strip_1p2

  route_4_TR:
    links:
      mzi_1,o4: tapered_input_coupler_4,o2
    settings:
      cross_section: strip_1p2
"""
    },
  {
    "name": "Ring Resonator with Edge Couplers on Both Sides (Functional Example)",
        "description": "A complete ring resonator circuit with edge couplers on both sides using proper relative placement syntax. Ring resonator is anchored at (0,0), the edge couplers use 'to:' syntax for relative placement. All routes properly connect ports.",
        "yaml": """
    name: ring_resonator_edge_couplers

instances:
  ring_1:
    component: ring_resonator
    settings: 
      radius: 200.0
      isDoubleSided: False

  tapered_input_coupler_1: # BL (Bottom Left)
    component: tapered_input_coupler
    settings: {}
  
  tapered_input_coupler_2: # BR (Bottom Right)
    component: tapered_input_coupler
    settings: {}


placements:
  # ANCHOR: Ring at absolute position (0, 0)
  ring_1:
    x: 0
    y: 0
    rotation: 0

  # RELATIVE: Tapers connect to MZI ports with offsets
  # --- LEFT SIDE (Inputs) ---
  tapered_input_coupler_1: # Bottom Left
    to: ring_1,o1
    port: o2
    dx: -200
    dy: 0
    rotation: 0

  tapered_input_coupler_2: # Bottom Right
    to: ring_1,o2
    port: o2
    dx: 200
    dy: 0
    rotation: 0


routes:
  route_1_input:
    links:
      tapered_input_coupler_1,o2: ring_1,o1
    settings:
      cross_section: strip_1p2

  route_2_through:
    links:
      tapered_input_coupler_2,o2: ring_1,o2
    settings:
      cross_section: strip_1p2
"""
  },
  {
    "name": "Ring Resonator with Edge Couplers on input and grating couplers on add and drop ports",
        "description": "A complete ring resonator circuit with edge couplers on input and grating couplers on add and drop ports using proper relative placement syntax. Ring resonator is anchored at (0,0), the edge couplers use 'to:' syntax for relative placement. All routes properly connect ports.",
        "yaml": """
    name: ring_resonator_edge_couplers_grating_couplers

  instances:
    ring_1:
      component: ring_resonator
      settings: 
        radius: 200.0
        isDoubleSided: True

    tapered_input_coupler_1: # BL (Bottom Left)
      component: tapered_input_coupler
      settings: {}
    
    grating_coupler_1: # TL (Top Left)
      component: focusing_grating_coupler
      settings: {}

    grating_coupler_2: # TR (Top Right)
      component: focusing_grating_coupler
      settings: {}

  placements:
    # ANCHOR: Ring at absolute position (0, 0)
    ring_1:
      x: 0
      y: 0
      rotation: 0

    # RELATIVE: Tapers connect to MZI ports with offsets
    # --- LEFT SIDE (Inputs) ---
    tapered_input_coupler_1: # Bottom Left
      to: ring_1,o1
      port: o2
      dx: -200
      dy: 0
      rotation: 0

    grating_coupler_1: # Top Left
      to: ring_1,o4
      port: o1
      dx: 0
      dy: 0
      rotation: 0

    grating_coupler_2: # Top Right
      to: ring_1,o3
      port: o1
      dx: 0
      dy: 0
      rotation: 0


  routes:
    route_1_input:
      links:
        tapered_input_coupler_1,o2: ring_1,o1
      settings:
        cross_section: strip_1p2

    route_2_add:
      links:
        grating_coupler_1,o1: ring_1,o4
      settings:
        cross_section: strip_1p2
    route_3_drop:
      links:
        ring_1,o3: grating_coupler_2,o1
      settings:
        cross_section: strip_1p2
  """
  },
    {
    "name": "Loopback mirror with grating couplers",
    "description": "MZI anchor with ports o1 and o2 connected to grating couplers, and o3 and o4 routed together with an euler bend",
    "yaml": """
  name: loopback_mirror_grating_couplers

  instances:
    mzi_1:
      component: mzi_no_heater
      settings: 
        arm_spacing: 200.0
        mzi_arm_length: 1000.0

    grating_coupler_1: # Bottom Left
      component: focusing_grating_coupler
      settings: {}
    
    grating_coupler_2: # Top Left
      component: focusing_grating_coupler
      settings: {}
    
    euler_bend_1: # Euler Bend connecting o3 and o4
      component: euler_bend
      settings: 
        radius: 91.7
        angle: 180.0
        

  placements:
    # ANCHOR: MZI at absolute position (0, 0)
    mzi_1:
      x: 0
      y: 0
      rotation: 0

    # RELATIVE: Tapers connect to MZI ports with offsets
    # --- LEFT SIDE (Inputs) ---
    grating_coupler_1: # Bottom Left
      to: mzi_1,o1
      port: o1
      dx: 0
      dy: 0
      rotation: 0

    grating_coupler_2: # Top Left
      to: mzi_1,o2
      port: o1
      dx: 0
      dy: 0
      rotation: 0

    euler_bend_1: # Bottom Right
      to: mzi_1,o3
      port: o1
      dx: 0
      dy: 0
      rotation: 0


  routes:
    route_1_input_1:
      links:
        grating_coupler_1,o1: mzi_1,o1
      settings:
        cross_section: strip_1p2

    route_2_input_2:
      links:
        grating_coupler_2,o1: mzi_1,o2
      settings:
        cross_section: strip_1p2
    route_3_loopback:
      links:
        mzi_1,o3: euler_bend_1,o1
      settings:
        cross_section: strip_1p2
  """
  }
]
