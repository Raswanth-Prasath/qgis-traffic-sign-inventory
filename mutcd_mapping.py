"""
MUTCD Mapping Table & Point Feature Info
Maps Mapillary object_value strings to MUTCD sign codes/descriptions,
and point feature values to categories/descriptions.
"""

# ===================================================================
# TRAFFIC SIGN MAPPING: Mapillary value -> (MUTCD code, desc, category)
# ===================================================================

MAPILLARY_TO_MUTCD = {
    # ===== REGULATORY =====

    # Stop / Yield
    'regulatory--stop--g1':                          ('R1-1', 'Stop', 'regulatory'),
    'regulatory--yield--g1':                         ('R1-2', 'Yield', 'regulatory'),
    'regulatory--all-way--g1':                       ('R1-3', 'All Way', 'regulatory'),

    # Speed Limits
    'regulatory--speed-limit-5--g3':                 ('R2-1', 'Speed Limit 5', 'regulatory'),
    'regulatory--speed-limit-10--g3':                ('R2-1', 'Speed Limit 10', 'regulatory'),
    'regulatory--speed-limit-15--g3':                ('R2-1', 'Speed Limit 15', 'regulatory'),
    'regulatory--speed-limit-20--g3':                ('R2-1', 'Speed Limit 20', 'regulatory'),
    'regulatory--speed-limit-25--g3':                ('R2-1', 'Speed Limit 25', 'regulatory'),
    'regulatory--speed-limit-30--g3':                ('R2-1', 'Speed Limit 30', 'regulatory'),
    'regulatory--speed-limit-35--g3':                ('R2-1', 'Speed Limit 35', 'regulatory'),
    'regulatory--speed-limit-40--g3':                ('R2-1', 'Speed Limit 40', 'regulatory'),
    'regulatory--speed-limit-45--g3':                ('R2-1', 'Speed Limit 45', 'regulatory'),
    'regulatory--speed-limit-50--g3':                ('R2-1', 'Speed Limit 50', 'regulatory'),
    'regulatory--speed-limit-55--g3':                ('R2-1', 'Speed Limit 55', 'regulatory'),
    'regulatory--speed-limit-60--g3':                ('R2-1', 'Speed Limit 60', 'regulatory'),
    'regulatory--speed-limit-65--g3':                ('R2-1', 'Speed Limit 65', 'regulatory'),
    'regulatory--speed-limit-70--g3':                ('R2-1', 'Speed Limit 70', 'regulatory'),
    'regulatory--speed-limit-75--g3':                ('R2-1', 'Speed Limit 75', 'regulatory'),
    'regulatory--maximum-speed-limit-15--g3':        ('R2-1', 'Speed Limit 15', 'regulatory'),
    'regulatory--maximum-speed-limit-20--g3':        ('R2-1', 'Speed Limit 20', 'regulatory'),
    'regulatory--maximum-speed-limit-25--g3':        ('R2-1', 'Speed Limit 25', 'regulatory'),
    'regulatory--maximum-speed-limit-30--g3':        ('R2-1', 'Speed Limit 30', 'regulatory'),
    'regulatory--maximum-speed-limit-35--g3':        ('R2-1', 'Speed Limit 35', 'regulatory'),
    'regulatory--maximum-speed-limit-40--g3':        ('R2-1', 'Speed Limit 40', 'regulatory'),
    'regulatory--maximum-speed-limit-45--g3':        ('R2-1', 'Speed Limit 45', 'regulatory'),
    'regulatory--maximum-speed-limit-50--g3':        ('R2-1', 'Speed Limit 50', 'regulatory'),
    'regulatory--maximum-speed-limit-55--g3':        ('R2-1', 'Speed Limit 55', 'regulatory'),
    'regulatory--maximum-speed-limit-60--g3':        ('R2-1', 'Speed Limit 60', 'regulatory'),
    'regulatory--maximum-speed-limit-65--g3':        ('R2-1', 'Speed Limit 65', 'regulatory'),

    # Turn / Movement
    'regulatory--no-left-turn--g1':                  ('R3-2', 'No Left Turn', 'regulatory'),
    'regulatory--no-right-turn--g1':                 ('R3-1', 'No Right Turn', 'regulatory'),
    'regulatory--no-u-turn--g1':                     ('R3-4', 'No U-Turn', 'regulatory'),
    'regulatory--no-straight-through--g1':           ('R3-27', 'No Straight Through', 'regulatory'),
    'regulatory--turn-right--g1':                    ('R3-5R', 'Right Turn Only', 'regulatory'),
    'regulatory--turn-left--g1':                     ('R3-5L', 'Left Turn Only', 'regulatory'),
    'regulatory--go-straight--g1':                   ('R3-5a', 'Straight Only', 'regulatory'),
    'regulatory--turn-right-ahead--g1':              ('R3-5R', 'Right Turn Ahead', 'regulatory'),
    'regulatory--left-turn-yield-on-green--g1':      ('R10-12', 'Left Turn Yield on Green', 'regulatory'),

    # One Way / Wrong Way / Entry
    'regulatory--one-way-left--g1':                  ('R6-1L', 'One Way Left', 'regulatory'),
    'regulatory--one-way-right--g1':                 ('R6-1R', 'One Way Right', 'regulatory'),
    'regulatory--one-way-straight--g1':              ('R6-1', 'One Way', 'regulatory'),
    'regulatory--do-not-enter--g1':                  ('R5-1', 'Do Not Enter', 'regulatory'),
    'regulatory--wrong-way--g1':                     ('R5-1a', 'Wrong Way', 'regulatory'),
    'regulatory--road-closed--g1':                   ('R11-2', 'Road Closed', 'regulatory'),
    'regulatory--road-closed-to-vehicles--g1':       ('R11-2', 'Road Closed', 'regulatory'),

    # Lane Use
    'regulatory--keep-right--g1':                    ('R4-7', 'Keep Right', 'regulatory'),
    'regulatory--keep-left--g1':                     ('R4-8', 'Keep Left', 'regulatory'),
    'regulatory--pass-on-either-side--g1':           ('R4-9', 'Pass Either Side', 'regulatory'),

    # Parking / Stopping
    'regulatory--no-parking--g1':                    ('R8-3', 'No Parking', 'regulatory'),
    'regulatory--no-stopping-or-standing--g1':       ('R7-4', 'No Stopping', 'regulatory'),
    'regulatory--no-parking-or-no-stopping--g1':     ('R8-3', 'No Parking', 'regulatory'),

    # Pedestrian / Bicycle
    'regulatory--no-pedestrians--g1':                ('R9-3', 'No Pedestrians', 'regulatory'),
    'regulatory--pedestrians-only--g1':              ('R9-3a', 'Pedestrians Only', 'regulatory'),
    'regulatory--no-bicycles--g1':                   ('R5-6', 'No Bicycles', 'regulatory'),
    'regulatory--shared-path-bicycles-and-pedestrians--g1': ('R9-7', 'Shared Path', 'regulatory'),

    # Trucks / Weight
    'regulatory--no-heavy-goods-vehicles--g1':       ('R5-2', 'No Trucks', 'regulatory'),
    'regulatory--weight-limit--g1':                  ('R12-1', 'Weight Limit', 'regulatory'),
    'regulatory--height-limit--g1':                  ('R12-4', 'Height Limit', 'regulatory'),

    # ===== WARNING =====

    # Curves
    'warning--curve-left--g1':                       ('W1-2L', 'Curve Left', 'warning'),
    'warning--curve-right--g1':                      ('W1-2R', 'Curve Right', 'warning'),
    'warning--sharp-curve-left--g1':                 ('W1-1L', 'Sharp Curve Left', 'warning'),
    'warning--sharp-curve-right--g1':                ('W1-1R', 'Sharp Curve Right', 'warning'),
    'warning--winding-road--g1':                     ('W1-5', 'Winding Road', 'warning'),
    'warning--reverse-curve-left--g1':               ('W1-4L', 'Reverse Curve Left', 'warning'),
    'warning--reverse-curve-right--g1':              ('W1-4R', 'Reverse Curve Right', 'warning'),
    'warning--hairpin-curve-left--g1':               ('W1-11L', 'Hairpin Curve Left', 'warning'),
    'warning--hairpin-curve-right--g1':              ('W1-11R', 'Hairpin Curve Right', 'warning'),

    # Intersections
    'warning--crossroads--g1':                       ('W2-1', 'Cross Road', 'warning'),
    'warning--t-roads--g1':                          ('W2-4', 'T Intersection', 'warning'),
    'warning--y-roads--g1':                          ('W2-5', 'Y Intersection', 'warning'),
    'warning--roundabout--g1':                       ('W2-6', 'Roundabout', 'warning'),
    'warning--side-road-left--g1':                   ('W2-2L', 'Side Road Left', 'warning'),
    'warning--side-road-right--g1':                  ('W2-2R', 'Side Road Right', 'warning'),

    # Signals / Signs Ahead
    'warning--stop-ahead--g1':                       ('W3-1', 'Stop Ahead', 'warning'),
    'warning--yield-ahead--g1':                      ('W3-2', 'Yield Ahead', 'warning'),
    'warning--signal-ahead--g1':                     ('W3-3', 'Signal Ahead', 'warning'),

    # Merge / Lane
    'warning--merging-traffic--g1':                  ('W4-1', 'Merge', 'warning'),
    'warning--added-lane--g1':                       ('W4-3', 'Added Lane', 'warning'),
    'warning--lane-ends--g1':                        ('W4-2', 'Lane Ends', 'warning'),

    # Road Narrowing
    'warning--road-narrows--g1':                     ('W5-1', 'Road Narrows', 'warning'),
    'warning--road-narrows-left--g1':                ('W5-2L', 'Narrows Left', 'warning'),
    'warning--road-narrows-right--g1':               ('W5-2R', 'Narrows Right', 'warning'),
    'warning--narrow-bridge--g1':                    ('W5-2', 'Narrow Bridge', 'warning'),

    # Divided Highway
    'warning--divided-highway-ends--g1':             ('W6-2', 'Divided Hwy Ends', 'warning'),
    'warning--two-way-traffic--g1':                  ('W6-3', 'Two Way Traffic', 'warning'),

    # Hill / Grade
    'warning--hill--g1':                             ('W7-1', 'Hill', 'warning'),
    'warning--steep-ascent--g1':                     ('W7-1', 'Steep Ascent', 'warning'),
    'warning--steep-descent--g1':                    ('W7-1', 'Steep Descent', 'warning'),

    # Road Conditions
    'warning--slippery-road-surface--g1':            ('W8-5', 'Slippery When Wet', 'warning'),
    'warning--bump--g1':                             ('W8-1', 'Bump', 'warning'),
    'warning--dip--g1':                              ('W8-2', 'Dip', 'warning'),
    'warning--uneven-road--g1':                      ('W8-15', 'Uneven Road', 'warning'),
    'warning--road-bump--g1':                        ('W8-1', 'Speed Bump', 'warning'),
    'warning--flooding--g1':                         ('W8-18', 'Flood Area', 'warning'),
    'warning--falling-rocks-or-debris-right--g1':    ('W8-10', 'Falling Rocks', 'warning'),

    # Crossings
    'warning--pedestrians-crossing--g1':             ('W11-2', 'Pedestrian Crossing', 'warning'),
    'warning--school-zone--g1':                      ('S1-1', 'School Zone', 'warning'),
    'warning--children--g1':                         ('W15-1', 'Playground', 'warning'),
    'warning--bicycles-crossing--g1':                ('W11-1', 'Bicycle Crossing', 'warning'),
    'warning--railroad-crossing--g1':                ('W10-1', 'Railroad Crossing', 'warning'),
    'warning--railroad-crossing-with-gates--g1':     ('W10-1', 'RR Crossing Gates', 'warning'),
    'warning--deer-crossing--g1':                    ('W11-3', 'Deer Crossing', 'warning'),
    'warning--cattle--g1':                           ('W11-4', 'Cattle Crossing', 'warning'),
    'warning--equestrians--g1':                      ('W11-7', 'Equestrian Crossing', 'warning'),

    # Other Warning
    'warning--dead-end--g1':                         ('W14-1', 'Dead End', 'warning'),
    'warning--dead-end--g3':                         ('W14-1', 'Dead End', 'warning'),
    'warning--construction--g1':                     ('W20-1', 'Road Work Ahead', 'warning'),
    'warning--road-work-ahead--g1':                  ('W20-1', 'Road Work Ahead', 'warning'),
    'warning--double-curve-first-left--g1':          ('W1-4L', 'Double Curve Left', 'warning'),
    'warning--double-curve-first-right--g1':         ('W1-4R', 'Double Curve Right', 'warning'),
    'warning--trucks-crossing--g1':                  ('W8-6', 'Truck Crossing', 'warning'),
    'warning--low-clearance--g1':                    ('W12-2', 'Low Clearance', 'warning'),

    # ===== INFORMATION / GUIDE =====
    'information--parking--g1':                      ('D4-1', 'Parking', 'information'),
    'information--hospital--g1':                     ('D9-2', 'Hospital', 'information'),
    'information--airport--g1':                      ('I-5', 'Airport', 'information'),
    'information--interstate-route--g2':             ('M1-1', 'Interstate Route', 'information'),
    'information--highway-interstate-route--g2':     ('M1-1', 'Interstate Route', 'information'),
    'information--us-highway-route--g1':             ('M1-4', 'US Route', 'information'),
    'information--state-highway-route--g1':          ('M1-5', 'State Route', 'information'),
    'information--pedestrians-crossing--g1':         ('D9-12', 'Ped Crossing', 'information'),
    'information--dead-end--g1':                     ('W14-1', 'Dead End', 'information'),
    'information--dead-end--g3':                     ('W14-1', 'Dead End', 'information'),
    'information--gas-station--g1':                  ('D9-7', 'Gas Station', 'information'),
    'information--food--g1':                         ('D9-8', 'Food', 'information'),
    'information--lodging--g1':                      ('D9-9', 'Lodging', 'information'),
    'information--camping--g1':                      ('D9-3', 'Camping', 'information'),
    'information--telephone--g1':                    ('D9-1', 'Telephone', 'information'),
    'information--handicapped-accessible--g1':       ('D9-6', 'Accessible', 'information'),
    'information--bike-route--g1':                   ('D11-1', 'Bike Route', 'information'),
}


# ===================================================================
# POINT FEATURE MAPPING: Mapillary value -> (category, description)
# ===================================================================

POINT_FEATURE_INFO = {
    # Signals
    'object--traffic-light--':                       ('signal', 'Traffic Light'),
    'object--traffic-light--general-upright':         ('signal', 'Traffic Light (Upright)'),
    'object--traffic-light--general-horizontal':      ('signal', 'Traffic Light (Horizontal)'),
    'object--traffic-light--pedestrians':             ('signal', 'Pedestrian Signal'),
    'object--traffic-light--cyclists':                ('signal', 'Cyclist Signal'),

    # Markings - Crosswalks / Stop Lines
    'marking--crosswalk-zebra':                      ('marking', 'Crosswalk (Zebra)'),
    'marking--crosswalk-plain':                      ('marking', 'Crosswalk (Plain)'),
    'marking--crosswalk-ladder':                     ('marking', 'Crosswalk (Ladder)'),
    'marking--stop-line':                            ('marking', 'Stop Line'),
    'marking--give-way-row':                         ('marking', 'Yield Line'),
    'marking--give-way-single':                      ('marking', 'Yield Line (Single)'),

    # Markings - Lane Arrows / Symbols
    'marking--arrow--straight':                      ('marking', 'Lane Arrow (Straight)'),
    'marking--arrow--left':                          ('marking', 'Lane Arrow (Left)'),
    'marking--arrow--right':                         ('marking', 'Lane Arrow (Right)'),
    'marking--arrow--split-left-straight':            ('marking', 'Lane Arrow (Left+Straight)'),
    'marking--arrow--split-right-straight':           ('marking', 'Lane Arrow (Right+Straight)'),
    'marking--arrow--u-turn':                        ('marking', 'Lane Arrow (U-Turn)'),
    'marking--symbol--bicycle':                      ('marking', 'Bike Lane Symbol'),
    'marking--symbol--wheelchair':                   ('marking', 'Wheelchair Symbol'),

    # Infrastructure
    'object--fire-hydrant':                          ('infrastructure', 'Fire Hydrant'),
    'object--street-light':                          ('infrastructure', 'Street Light'),
    'object--utility-pole':                          ('infrastructure', 'Utility Pole'),
    'object--manhole':                               ('infrastructure', 'Manhole'),
    'object--catch-basin':                           ('infrastructure', 'Catch Basin'),
    'object--water-valve':                           ('infrastructure', 'Water Valve'),
    'object--phone-booth':                           ('infrastructure', 'Phone Booth'),
    'object--mailbox':                               ('infrastructure', 'Mailbox'),

    # Furniture
    'object--bench':                                 ('furniture', 'Bench'),
    'object--trash-can':                             ('furniture', 'Trash Can'),
    'object--bike-rack':                             ('furniture', 'Bike Rack'),
    'object--parking-meter':                         ('furniture', 'Parking Meter'),
    'object--bollard':                               ('furniture', 'Bollard'),

    # Traffic Control
    'object--traffic-cone':                          ('traffic_control', 'Traffic Cone'),
    'object--temporary-barrier':                     ('traffic_control', 'Temporary Barrier'),
    'object--jersey-barrier':                        ('traffic_control', 'Jersey Barrier'),
}


# ===================================================================
# HELPER FUNCTIONS — SIGNS
# ===================================================================

def get_mutcd(mapillary_value):
    """Look up MUTCD code for a Mapillary sign value.

    Returns:
        tuple: (mutcd_code, description, category) or (None, auto_description, auto_category)
    """
    if mapillary_value in MAPILLARY_TO_MUTCD:
        return MAPILLARY_TO_MUTCD[mapillary_value]

    # Auto-generate description from Mapillary value
    parts = mapillary_value.split('--')
    category = parts[0] if parts else 'unknown'
    name = parts[1].replace('-', ' ').title() if len(parts) > 1 else mapillary_value
    return (None, name, category)


def get_all_sign_values():
    """Return list of all mapped Mapillary sign values."""
    return list(MAPILLARY_TO_MUTCD.keys())


def get_category_values(category):
    """Return all sign values for a given category (regulatory, warning, information)."""
    return [k for k, v in MAPILLARY_TO_MUTCD.items() if v[2] == category]


# ===================================================================
# HELPER FUNCTIONS — POINT FEATURES
# ===================================================================

def get_point_info(mapillary_value):
    """Look up category and description for a Mapillary point feature value.

    Returns:
        tuple: (category, description) with fallback for unmapped values
    """
    if mapillary_value in POINT_FEATURE_INFO:
        return POINT_FEATURE_INFO[mapillary_value]

    # Fallback: derive category from value prefix
    parts = mapillary_value.split('--')
    category = parts[0] if parts else 'unknown'
    desc = mapillary_value.replace('--', ' ').replace('-', ' ').title()
    return (category, desc)


def get_point_category_values(category):
    """Return all point feature values for a given category."""
    return [k for k, v in POINT_FEATURE_INFO.items() if v[0] == category]
