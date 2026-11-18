"""Synthetic complaint dataset generator for HostelOps demo.

This is sample data created for the demo, not real hostel data.
Run with: python -m ml.generate_data
"""
import os
import random

import pandas as pd

# Category names defined locally (do not import the Flask app)
CATEGORIES = [
    'Water',
    'Electricity',
    'Wi-Fi',
    'Mess',
    'Cleanliness',
    'Furniture',
    'Other',
]

PLACES = [
    'block A',
    'block B',
    'room 204',
    'the second floor',
    'my room',
    'the ground floor washroom',
    'the corridor',
    'block C',
    'room 101',
    'the common room',
]

TIMES = [
    'since last night',
    'for two days',
    'this morning',
    'for 3 hours',
    'since yesterday evening',
    'for a week',
    'since Monday',
    'since the last two days',
]

# Templates: (text_template, priority)
# Each category has at least 12 unique templates
TEMPLATES = {
    'Water': [
        ('No water in {place} {when}', 'High'),
        ('Tap is leaking in {place}', 'High'),
        ('Water cooler near {place} is not working', 'Low'),
        ('Water supply has been cut off in {place} {when}', 'High'),
        ('The overhead tank in {place} is overflowing', 'High'),
        ('No hot water in {place} {when}', 'Medium'),
        ('Water pressure is very low in {place}', 'Medium'),
        ('Drain pipe is blocked in {place}', 'Medium'),
        ('Washroom tap dripping constantly in {place}', 'Medium'),
        ('No drinking water available near {place} {when}', 'High'),
        ('Water pipe burst in {place}', 'High'),
        ('Water cooler is leaking in {place}', 'Medium'),
        ('The flush in {place} is not working {when}', 'Medium'),
        ('Water logging in {place} {when}', 'High'),
        ('Tap handle broken in {place}', 'Low'),
        ('No water in washroom of {place} {when}', 'High'),
        ('Water filter needs replacement in {place}', 'Low'),
        ('Sewage smell coming from drain in {place}', 'Medium'),
    ],
    'Electricity': [
        ('Power cut in {place} {when}', 'High'),
        ('Sparks coming from the switch board in {place}', 'High'),
        ('Tube light in {place} needs replacing', 'Low'),
        ('Fan is not working in {place} {when}', 'Medium'),
        ('Electric shock from socket in {place}', 'High'),
        ('Lights not working in {place} {when}', 'High'),
        ('Switchboard burnt in {place}', 'High'),
        ('AC unit not cooling in {place}', 'Medium'),
        ('Power fluctuation in {place} {when}', 'Medium'),
        ('Bulb fused in {place}', 'Low'),
        ('No electricity in {place} {when}', 'High'),
        ('Generator not starting in {place}', 'High'),
        ('Extension board damaged in {place}', 'Medium'),
        ('Ceiling fan wobbling dangerously in {place}', 'High'),
        ('Street light outside {place} not working', 'Low'),
        ('MCB tripping repeatedly in {place} {when}', 'High'),
        ('Heater not working in {place}', 'Medium'),
        ('UPS battery dead in {place}', 'Medium'),
    ],
    'Wi-Fi': [
        ('Wi-Fi is not working in {place} {when}', 'Medium'),
        ('wifi nt working again in {place}', 'Medium'),
        ('No internet connectivity in {place} {when}', 'Medium'),
        ('Wi-Fi speed is very slow in {place}', 'Low'),
        ('Wi-Fi router needs restart in {place}', 'Low'),
        ('Cannot connect to hostel wifi in {place} {when}', 'Medium'),
        ('Wi-Fi password not working in {place}', 'Low'),
        ('Network drops every few minutes in {place}', 'Medium'),
        ('Wi-Fi signal too weak in {place}', 'Low'),
        ('Internet down completely in {place} {when}', 'High'),
        ('Router offline in {place} {when}', 'Medium'),
        ('WiFi disconnects at night in {place}', 'Medium'),
        ('No wifi coverage in {place}', 'Medium'),
        ('Slow upload speed in {place} {when}', 'Low'),
        ('Wi-Fi login page not loading in {place}', 'Medium'),
        ('Network cable unplugged in {place}', 'Low'),
        ('Wifi has been down {when} in {place}', 'High'),
        ('Cannot attend online classes due to no wifi in {place}', 'High'),
    ],
    'Mess': [
        ('Food served in the mess {when} was stale', 'Medium'),
        ('Mess food quality is very poor {when}', 'Medium'),
        ('Cockroaches found in mess food {when}', 'High'),
        ('No vegetables served in mess {when}', 'Medium'),
        ('Mess is closed earlier than scheduled {when}', 'High'),
        ('Food is undercooked in the mess {when}', 'Medium'),
        ('Mess menu is not being followed {when}', 'Low'),
        ('No drinking water in mess {when}', 'High'),
        ('Mess utensils are dirty {when}', 'Medium'),
        ('Food has bad smell in mess {when}', 'High'),
        ('Long queue at mess counter {when}', 'Low'),
        ('Mess workers behaving rudely {when}', 'Medium'),
        ('Mess closed without notice {when}', 'High'),
        ('Mess food has insects {when}', 'High'),
        ('Unhygienic conditions in mess {when}', 'High'),
        ('Insufficient quantity of food in mess {when}', 'Medium'),
        ('Mess menu board is outdated', 'Low'),
        ('No breakfast served in mess {when}', 'High'),
    ],
    'Cleanliness': [
        ('Washroom in {place} is very dirty', 'Medium'),
        ('Garbage not collected in {place} {when}', 'Medium'),
        ('Foul smell in {place} {when}', 'Medium'),
        ('Dustbin overflowing in {place}', 'Medium'),
        ('Corridor in {place} is very dirty {when}', 'Medium'),
        ('Sweeping not done in {place} {when}', 'Low'),
        ('Stagnant water on floor of {place}', 'High'),
        ('Rats seen in {place} {when}', 'High'),
        ('Cleaning staff not coming to {place} {when}', 'Medium'),
        ('Mould on walls of {place}', 'Medium'),
        ('Washroom tiles very slippery in {place}', 'High'),
        ('Pests in {place} {when}', 'High'),
        ('Bathroom drain blocked in {place}', 'Medium'),
        ('Litter everywhere in {place}', 'Low'),
        ('Washroom mirror broken in {place}', 'Low'),
        ('Toilet seat broken in {place}', 'Medium'),
        ('No soap or sanitizer in {place} {when}', 'Medium'),
        ('Garbage dumped outside {place}', 'Medium'),
    ],
    'Furniture': [
        ('Chair in {place} has a broken leg', 'Low'),
        ('Table in {place} is damaged', 'Low'),
        ('Bed frame broken in {place}', 'Medium'),
        ('Wardrobe door not closing in {place}', 'Low'),
        ('Study chair missing in {place}', 'Low'),
        ('Bookshelf collapsed in {place}', 'Medium'),
        ('Mattress is torn in {place}', 'Low'),
        ('Window latch broken in {place}', 'Medium'),
        ('Door lock not working in {place}', 'High'),
        ('Cupboard hinge broken in {place}', 'Low'),
        ('Bed mattress has bugs in {place}', 'High'),
        ('Study table wobbly in {place}', 'Low'),
        ('Almirah key missing for room in {place}', 'Medium'),
        ('Window glass cracked in {place}', 'Medium'),
        ('Curtain rod fallen in {place}', 'Low'),
        ('Broken stool in {place}', 'Low'),
        ('Drawer stuck in {place}', 'Low'),
        ('Room door not closing properly in {place}', 'Medium'),
    ],
    'Other': [
        ('Please add a notice board near {place}', 'Low'),
        ('Security guard not present at gate {when}', 'High'),
        ('No parking space available near {place}', 'Low'),
        ('Common room TV not working {when}', 'Low'),
        ('Noise disturbance in {place} {when}', 'Medium'),
        ('Lift not working in {place} {when}', 'High'),
        ('Fire extinguisher missing from {place}', 'High'),
        ('First aid kit not available near {place}', 'High'),
        ('Request for extra blanket in {place}', 'Low'),
        ('No hot water in common bathroom {when}', 'Medium'),
        ('CCTV camera not working in {place}', 'High'),
        ('Bike parking area messy near {place}', 'Low'),
        ('Common room lock broken in {place}', 'Medium'),
        ('Lost and found box needed near {place}', 'Low'),
        ('Need iron stand in {place}', 'Low'),
        ('Staircase light not working in {place} {when}', 'Medium'),
        ('Gym equipment broken near {place}', 'Medium'),
        ('Suggestion: add water cooler near {place}', 'Low'),
    ],
}


def _expand_templates(category, templates, places, times):
    """Expand templates with place/time fillers into unique rows."""
    rows = []
    for tmpl, priority in templates:
        if '{place}' in tmpl and '{when}' in tmpl:
            for place in places:
                for when in times[:4]:  # limit combos to control total size
                    text = tmpl.format(place=place, when=when)
                    rows.append((text, category, priority))
        elif '{place}' in tmpl:
            for place in places:
                text = tmpl.format(place=place)
                rows.append((text, category, priority))
        elif '{when}' in tmpl:
            for when in times:
                text = tmpl.format(when=when)
                rows.append((text, category, priority))
        else:
            rows.append((tmpl, category, priority))
    return rows


def generate(output_path=None):
    """Generate the synthetic dataset and write to CSV."""
    random.seed(42)

    if output_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(here, 'data', 'complaints.csv')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    all_rows = []
    for category in CATEGORIES:
        templates = TEMPLATES[category]
        rows = _expand_templates(category, templates, PLACES, TIMES)
        all_rows.extend(rows)

    # Remove duplicate texts
    seen = set()
    unique_rows = []
    for text, cat, pri in all_rows:
        if text not in seen:
            seen.add(text)
            unique_rows.append({'text': text, 'category': cat, 'priority': pri})

    # Shuffle deterministically
    random.shuffle(unique_rows)

    df = pd.DataFrame(unique_rows, columns=['text', 'category', 'priority'])
    df.to_csv(output_path, index=False)
    print(
        f"Generated {len(df)} rows across "
        f"{df['category'].nunique()} categories -> {output_path}"
    )
    return df


if __name__ == '__main__':
    generate()
