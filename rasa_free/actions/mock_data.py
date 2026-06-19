"""
mock_data.py
============
Fallback datasets used when real APIs (Climatiq, Amadeus) are unavailable.
Activated automatically when USE_MOCK_DATA=true in .env or when API calls fail.
All carbon figures are representative estimates; real API data should be used
in production.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CARBON FOOTPRINT MOCK DATA
# kg CO₂e per person for representative routes and transport modes
# Sources: EEA (2023), Our World in Data (2023)
# ─────────────────────────────────────────────────────────────────────────────
CARBON_DATA = {
    # Format: (origin_lower, destination_lower, transport_mode): kg_co2e
    ("berlin", "amsterdam", "flight"): 95.4,
    ("berlin", "amsterdam", "train"): 8.1,
    ("berlin", "amsterdam", "bus"): 22.3,
    ("berlin", "amsterdam", "car"): 71.2,

    ("london", "barcelona", "flight"): 168.2,
    ("london", "barcelona", "train"): 19.7,  # via Eurostar + TGV
    ("london", "barcelona", "bus"): 39.8,

    ("paris", "lisbon", "flight"): 145.6,
    ("paris", "lisbon", "train"): 24.3,
    ("paris", "lisbon", "bus"): 44.1,

    ("berlin", "rome", "flight"): 182.1,
    ("berlin", "rome", "train"): 31.4,
    ("berlin", "rome", "car"): 118.7,

    ("london", "amsterdam", "flight"): 75.3,
    ("london", "amsterdam", "train"): 6.2,  # Eurostar
    ("london", "amsterdam", "ferry"): 47.8,

    ("paris", "barcelona", "flight"): 92.4,
    ("paris", "barcelona", "train"): 3.8,   # TGV — very low (French nuclear grid)

    ("berlin", "copenhagen", "flight"): 88.2,
    ("berlin", "copenhagen", "train"): 11.4,

    ("munich", "vienna", "flight"): 52.1,
    ("munich", "vienna", "train"): 5.6,
    ("munich", "vienna", "car"): 38.9,

    ("london", "edinburgh", "flight"): 62.4,
    ("london", "edinburgh", "train"): 9.0,
    ("london", "edinburgh", "bus"): 19.7,
}

# Per-km emission factors (kg CO₂e per passenger-km) as fallback
EMISSION_FACTORS = {
    "flight":        0.255,   # short-haul average (with radiative forcing)
    "train":         0.041,   # European average
    "bus":           0.089,   # coach average
    "car":           0.192,   # petrol car (1.5 occupants)
    "electric_car":  0.053,   # EU average grid intensity
    "ferry":         0.113,
    "metro":         0.029,
    "bike":          0.0,
    "walking":       0.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# ECO HOTEL MOCK DATA
# ─────────────────────────────────────────────────────────────────────────────
ECO_HOTELS = {
    "amsterdam": [
        {
            "name": "Hotel V Nesplein",
            "eco_cert": "Green Key",
            "rating": 8.4,
            "price_eur": 145,
            "eco_score": 0.88,
            "highlights": ["Solar panels", "Rainwater harvesting", "Local organic breakfast"],
            "address": "Nes 49, Amsterdam",
            "booking_url": "https://www.example.com/hotel-v-nesplein",
        },
        {
            "name": "INK Hotel Amsterdam",
            "eco_cert": "EarthCheck Silver",
            "rating": 8.7,
            "price_eur": 189,
            "eco_score": 0.82,
            "highlights": ["Carbon-neutral certified", "EV charging", "Zero single-use plastic"],
            "address": "Nieuwezijds Voorburgwal 67, Amsterdam",
            "booking_url": "https://www.example.com/ink-hotel",
        },
        {
            "name": "Hotel Not Hotel",
            "eco_cert": "Green Key",
            "rating": 8.1,
            "price_eur": 112,
            "eco_score": 0.79,
            "highlights": ["Upcycled furnishings", "Bicycle hire", "Low-energy lighting"],
            "address": "Piri Reisplein 34, Amsterdam",
            "booking_url": "https://www.example.com/hotel-not-hotel",
        },
    ],
    "lisbon": [
        {
            "name": "Bairro Alto Hotel",
            "eco_cert": "EarthCheck Gold",
            "rating": 9.1,
            "price_eur": 220,
            "eco_score": 0.91,
            "highlights": ["LEED certified", "Rooftop gardens", "Local artisan products"],
            "address": "Praça Luís de Camões 2, Lisbon",
            "booking_url": "https://www.example.com/bairro-alto",
        },
        {
            "name": "LX Boutique Hotel",
            "eco_cert": "Green Key",
            "rating": 8.3,
            "price_eur": 98,
            "eco_score": 0.84,
            "highlights": ["Solar thermal heating", "Plastic-free toiletries", "Bike sharing"],
            "address": "Rua do Alecrim 12, Lisbon",
            "booking_url": "https://www.example.com/lx-boutique",
        },
    ],
    "barcelona": [
        {
            "name": "Hotel Arts Barcelona",
            "eco_cert": "ISO 14001",
            "rating": 8.9,
            "price_eur": 310,
            "eco_score": 0.78,
            "highlights": ["Energy management system", "Local sourcing", "Water recycling"],
            "address": "Carrer de la Marina 19, Barcelona",
            "booking_url": "https://www.example.com/hotel-arts",
        },
        {
            "name": "Casa Camper Barcelona",
            "eco_cert": "Green Key",
            "rating": 8.6,
            "price_eur": 175,
            "eco_score": 0.87,
            "highlights": ["Zero-waste kitchen", "Rooftop terrace", "100% renewable energy"],
            "address": "Carrer d'Elisabets 11, Barcelona",
            "booking_url": "https://www.example.com/casa-camper",
        },
    ],
    "default": [
        {
            "name": "Eco Lodge Central",
            "eco_cert": "Green Key",
            "rating": 8.0,
            "price_eur": 120,
            "eco_score": 0.80,
            "highlights": ["Renewable energy", "Organic food", "Carbon offset programme"],
            "address": "City Centre",
            "booking_url": "#",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# TRANSPORT OPTIONS MOCK DATA
# ─────────────────────────────────────────────────────────────────────────────
TRANSPORT_OPTIONS = {
    ("berlin", "amsterdam"): [
        {
            "mode": "train",
            "operator": "Deutsche Bahn / NS International",
            "duration_hrs": 6.5,
            "price_eur": 49,
            "carbon_kg": 8.1,
            "co2_colour": "green",
            "eco_score": 0.95,
            "notes": "Direct ICE service; book 90 days ahead for best fares",
        },
        {
            "mode": "bus",
            "operator": "FlixBus",
            "duration_hrs": 8.5,
            "price_eur": 19,
            "carbon_kg": 22.3,
            "co2_colour": "green",
            "eco_score": 0.78,
            "notes": "Cheapest option; overnight service available",
        },
        {
            "mode": "flight",
            "operator": "easyJet / Ryanair",
            "duration_hrs": 1.5,
            "price_eur": 65,
            "carbon_kg": 95.4,
            "co2_colour": "red",
            "eco_score": 0.22,
            "notes": "Fastest but highest emissions; consider offset if chosen",
        },
    ],
    ("london", "amsterdam"): [
        {
            "mode": "train",
            "operator": "Eurostar",
            "duration_hrs": 4.0,
            "price_eur": 89,
            "carbon_kg": 6.2,
            "co2_colour": "green",
            "eco_score": 0.97,
            "notes": "Eurostar to Brussels, connect to Thalys/NS to Amsterdam",
        },
        {
            "mode": "ferry",
            "operator": "DFDS / Stena Line",
            "duration_hrs": 11.0,
            "price_eur": 55,
            "carbon_kg": 47.8,
            "co2_colour": "amber",
            "eco_score": 0.55,
            "notes": "Overnight ferry with cabin option; scenic experience",
        },
        {
            "mode": "flight",
            "operator": "British Airways / KLM",
            "duration_hrs": 1.25,
            "price_eur": 80,
            "carbon_kg": 75.3,
            "co2_colour": "red",
            "eco_score": 0.28,
            "notes": "Most frequent option but highest carbon; Eurostar recommended",
        },
    ],
    "default": [
        {
            "mode": "train",
            "operator": "Regional Rail",
            "duration_hrs": 4.0,
            "price_eur": 60,
            "carbon_kg": 15.0,
            "co2_colour": "green",
            "eco_score": 0.90,
            "notes": "Estimated train option",
        },
        {
            "mode": "flight",
            "operator": "Major carrier",
            "duration_hrs": 2.0,
            "price_eur": 120,
            "carbon_kg": 140.0,
            "co2_colour": "red",
            "eco_score": 0.25,
            "notes": "Estimated flight option",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# CULTURAL TIPS MOCK DATA
# ─────────────────────────────────────────────────────────────────────────────
CULTURAL_TIPS = {
    "amsterdam": {
        "eco_activities": [
            "Cycle through Vondelpark on a rented bike (OV-fiets available at stations)",
            "Visit Artis Royal Zoo — Dutch leader in wildlife conservation",
            "Take the free electric ferry to NDSM Wharf creative district",
            "Explore the Hortus Botanicus — one of Europe's oldest botanical gardens",
            "Join a canal clean-up with Plastic Whale",
        ],
        "responsible_tips": [
            "Use the GVB tram and metro — very low carbon per journey",
            "Eat at Mediamatic ETEN — zero-waste restaurant growing its own food",
            "Support local cooperative supermarkets (De School, Marqt)",
            "Book experiences through LocalBini for community-led tourism",
            "Respect the cycling infrastructure — it's the city's circulatory system",
        ],
        "sustainability_rating": "⭐⭐⭐⭐⭐ — Ranked #1 most sustainable city in Europe (EIU 2023)",
    },
    "lisbon": {
        "eco_activities": [
            "Explore the Arrábida Natural Park by electric bicycle",
            "Visit MAAT Museum — built sustainably on the Tagus riverbank",
            "Take the eco-certified wine tour in Setúbal Peninsula",
            "Join surf lessons with green-certified instructors in Cascais",
            "Explore Sintra's UNESCO forests and palaces by local bus",
        ],
        "responsible_tips": [
            "Use the Carris tram network (historic trams are iconic and low carbon)",
            "Try Time Out Market's local Portuguese produce stalls",
            "Stay in the Alfama district to support authentic community tourism",
            "Avoid busy Sintra on weekends; take the early train instead",
            "Carry a reusable water bottle — tap water is safe and excellent",
        ],
        "sustainability_rating": "⭐⭐⭐⭐ — Top 10 sustainable European capitals",
    },
    "barcelona": {
        "eco_activities": [
            "Walk or cycle the Greenways (Vías Verdes) network",
            "Visit Parc de Collserola — the largest urban forest in the world",
            "Take an electric boat tour of the harbour",
            "Join a sustainable food tour through Gràcia neighbourhood",
            "Visit Bunkers del Carmel for a carbon-free city panorama",
        ],
        "responsible_tips": [
            "Use the T-Casual metro pass — very affordable and low carbon",
            "Eat at Espai Mescladís — social enterprise restaurant",
            "Visit in shoulder season (May, October) to reduce overtourism pressure",
            "Support local Catalan artisans at Santa Caterina market",
            "Use Bicing public bike scheme (requires city registration)",
        ],
        "sustainability_rating": "⭐⭐⭐⭐ — Barcelona Superblock project reduces emissions 25%",
    },
    "default": {
        "eco_activities": [
            "Use public transport to explore the city",
            "Visit local farmers markets for fresh, sustainable produce",
            "Look for certified eco-tour operators for day trips",
            "Explore the city by bicycle where possible",
            "Support locally owned restaurants and shops",
        ],
        "responsible_tips": [
            "Carry a reusable water bottle and shopping bag",
            "Choose accommodations with environmental certifications",
            "Offset your travel carbon through a Gold Standard scheme",
            "Learn a few phrases in the local language to support community connection",
            "Leave wildlife and natural areas undisturbed",
        ],
        "sustainability_rating": "Information not available for this destination",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# CARBON OFFSET PROGRAMS MOCK DATA
# ─────────────────────────────────────────────────────────────────────────────
OFFSET_PROGRAMS = [
    {
        "name": "Gold Standard — Renewable Energy Kenya",
        "type": "Renewable Energy",
        "price_per_tonne_eur": 14.50,
        "certification": "Gold Standard (VER)",
        "project": "Wind farm replacing coal in western Kenya",
        "url": "https://www.goldstandard.org",
        "co_benefits": ["Community energy access", "Local jobs", "Air quality improvement"],
    },
    {
        "name": "Verified Carbon Standard — Amazon Forest Protection",
        "type": "Forest Protection (REDD+)",
        "price_per_tonne_eur": 12.00,
        "certification": "Verra VCS",
        "project": "Preventing 500,000 ha of Amazon deforestation",
        "url": "https://verra.org",
        "co_benefits": ["Biodiversity preservation", "Indigenous community support"],
    },
    {
        "name": "Atmosfair — Efficient Cookstoves India",
        "type": "Cookstoves / Energy Efficiency",
        "price_per_tonne_eur": 23.00,
        "certification": "Gold Standard",
        "project": "Replacing open fires with efficient stoves in rural India",
        "url": "https://www.atmosfair.de",
        "co_benefits": ["Health benefits", "Women's empowerment", "Forest preservation"],
    },
    {
        "name": "myclimate — Solar Energy Uganda",
        "type": "Renewable Energy",
        "price_per_tonne_eur": 16.80,
        "certification": "Gold Standard",
        "project": "Solar micro-grids for rural Ugandan communities",
        "url": "https://www.myclimate.org",
        "co_benefits": ["Energy access", "Education", "Local employment"],
    },
]
