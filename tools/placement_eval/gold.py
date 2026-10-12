"""The answer key: where each evaluation event really is, from reading its article.

Reference points come from OpenStreetMap and Google Maps where they agree
(checked on 9 October 2026; docs/placement-evaluation-2026-10-09.md). `exact` is the radius in km within which a
point counts as at the place (larger for a park, a lake, a long road or an
area); a stretch or several sites list several targets.
"""

T = {  # name: (lat, lon, exact_km)
    "chandapura": (12.8015, 77.7060, 0.8),
    "sanjaynagar main road": (13.0334, 77.5758, 0.6),
    "race course road blr": (12.9840, 77.5849, 0.6),
    "tank bund": (17.4215, 78.4845, 1.0),
    "hussain sagar": (17.4230, 78.4746, 1.2),
    "shalibanda x road": (17.3550, 78.4733, 0.4),
    "iiit junction": (17.4450, 78.3528, 0.4),
    "khajaguda junction": (17.4224, 78.3825, 0.4),
    "hitech city railway station": (17.4699, 78.3851, 0.4),
    "bolarum closures": (17.5100, 78.5280, 1.6),
    "kbr park": (17.4202, 78.4210, 0.8),
    "jubilee hills checkpost": (17.4266, 78.4156, 0.4),
    "clock tower rub": (17.4409, 78.4985, 0.4),
    "shaikpet flyover": (17.4048, 78.4062, 0.5),
    "nallakunta": (17.3975, 78.5056, 1.0),
    "bada ganesh": (17.4108, 78.4640, 0.4),
    "indira gandhi statue": (17.4148, 78.4658, 0.4),
    "secretariat junction": (17.4085, 78.4705, 0.4),
    "patancheru": (17.5286, 78.2674, 1.5),
    "isnapur junction": (17.5453, 78.2095, 0.5),
    "aparna neo mall": (17.4668, 78.3104, 0.4),
    "gandhi hospital": (17.4228, 78.5042, 0.5),
    "suraram vishwakarma colony": (17.5450, 78.4280, 1.0),
    "srinagar colony": (17.4321, 78.4385, 0.6),
    "picket": (17.4510, 78.4989, 0.8),
    "paramount colony gate 3": (17.4079, 78.4148, 0.5),
    "dlf gate 1 to gachibowli ps": (17.4468, 78.3528, 0.5),
    # Uncertain: neither source names the underpass; Hafeezpet station is the nearest named point.
    "vaishali nagar rub": (17.4826, 78.3631, 1.5),
    "ramnagar gundu": (17.4077, 78.5125, 0.6),
    "siddheshwar talao thane": (19.2015, 72.9675, 0.5),
    "shivaji park": (19.0287, 72.8392, 0.6),
}

# Title start -> targets, or "NONE" (no point is right) or "DIFFUSE" (city-wide; not scored).
KEY = {
    "Chandapura sees hours-long": ["chandapura"],
    "Heavy rain leaves Bengaluru roads": "NONE",
    "Sanjaynagar Main Road work": ["sanjaynagar main road"],
    "White topping work on Race Course Road": ["race course road blr"],
    "30,000 cops deployed": "DIFFUSE",
    "Bathukamma Festival": ["tank bund"],
    "Blocked roads, no transport": ["shalibanda x road"],
    "CMC accelerates H-CITI": ["iiit junction", "khajaguda junction"],
    "Cyberabad Waterlogging": ["hitech city railway station"],
    "Firearms heist solved": ["bolarum closures"],
    "GHMC redesigns KBR Park": ["kbr park", "jubilee hills checkpost"],
    "GHMC revises KBR Park": ["kbr park", "jubilee hills checkpost"],
    "Ganesh Immersion Procession Continues": "DIFFUSE",
    "Ganesh Immersion: Hyderabad Traffic Police": ["tank bund", "hussain sagar"],
    "HYDRAA teams clear waterlogging": ["clock tower rub"],
    "Heavy rain lashes Hyderabad": ["shaikpet flyover"],
    "Heavy rain, gusty winds": "DIFFUSE",
    "Hyderabad Market Road Crisis": ["nallakunta"],
    "Hyderabad police block roads around Tank Bund": ["tank bund", "hussain sagar"],
    "Hyderabad police issue Bada Ganesh": ["bada ganesh"],
    "Hyderabad residents flag blocked roads": "DIFFUSE",
    "Hyderabad traffic diversions: plan your route": ["indira gandhi statue", "secretariat junction"],
    "Hyderabad's 'Elevated Corridor'": ["kbr park", "jubilee hills checkpost"],
    "Hyderabad, northern Telangana receive": "DIFFUSE",
    "Hyderabad: Catchpits Pose": "DIFFUSE",
    "Hyderabad: Motorists stranded": ["hussain sagar", "tank bund"],
    "Hyderabad: Why Has the One-Way": ["kbr park"],
    "Hyderabad: Why has one-way": ["kbr park"],
    "Hyderabad’s KBR Park project": ["kbr park"],
    "KBR Park project faces rethink": ["kbr park"],
    "KBR flyover plan changed": ["kbr park", "jubilee hills checkpost"],
    "Khairatabad Ganesh pandal": ["bada ganesh"],
    "Khajaguda junction 60-day": ["khajaguda junction"],
    "NH-65 traffic diversion between Patancheru": ["patancheru"],
    "NH-65 traffic diversions at Isnapur": ["isnapur junction"],
    "Nallagandla Traffic Alert": ["aparna neo mall"],
    "Nine roads closed in Secunderabad Cantonment": ["bolarum closures"],
    "Potholes, sewage and stagnant water": ["gandhi hospital"],
    "Quthbullapur road works": ["suraram vishwakarma colony"],
    "Sangareddy-Patancheru": ["patancheru"],
    "Srinagar Colony Road Dug Up": ["srinagar colony"],
    "Stray cattle turn Picket": ["picket"],
    "Telangana Ministers, TPCC Chief": ["indira gandhi statue"],
    "Tolichowki residents troubled": ["paramount colony gate 3"],
    "Traffic Curbs Near IIIT Junction": ["dlf gate 1 to gachibowli ps", "iiit junction"],
    "Traffic diversions announced for Khairatabad": ["bada ganesh"],
    "Traffic diversions at Gachibowli": ["dlf gate 1 to gachibowli ps", "iiit junction"],
    "Traffic diversions at Khajaguda": ["khajaguda junction"],
    "Traffic restrictions at Hyderabad’s Vaishali": ["vaishali nagar rub"],
    "Traffic restrictions extended at Vaishali": ["vaishali nagar rub"],
    "Traffic restrictions imposed in Hyderabad ahead of PM": "DIFFUSE",
    "Traffic restrictions to continue in Hyderabad": "DIFFUSE",
    "Vaishali Nagar traffic restrictions": ["vaishali nagar rub"],
    "Whose silt is it anyway": ["ramnagar gundu"],
    "Wrong-Side Driving": ["jubilee hills checkpost"],
    "One injured after crane tilts": ["siddheshwar talao thane"],
    "SIR row: CJP": ["shivaji park"],
}

# Within this many km a point that is not exact still counts as close; beyond AREA_KM it is wrong.
CLOSE_KM = 1.0
AREA_KM = 3.0
SCORES = {"EXACT": 3, "CLOSE": 2, "AREA": 1, "MISSED": 0, "WRONG": -3, "RIGHTLY_NONE": 3, "SHOULD_BE_NONE": -2}


def targets_for(title: str):
    for start, value in KEY.items():
        if title.startswith(start):
            return value
    raise KeyError(title)
