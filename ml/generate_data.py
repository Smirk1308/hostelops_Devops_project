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
    'block C',
    'room 101',
    'room 204',
    'room 305',
    'my room',
    'the corridor',
    'the second floor',
    'the ground floor washroom',
    'the common room',
    'wing 2',
]

TIMES = [
    'since last night',
    'for two days',
    'this morning',
    'for 3 hours',
    'since yesterday evening',
    'for a week',
    'since Monday',
    'since yesterday',
]

# Curated list of template definitions per category.
# Balanced across priorities so all priorities appear realistic.
TEMPLATES = {
    'Water': [
        ('No water in {place} {when}', 'High'),
        ('Tap is leaking in {place}', 'High'),
        ('Water supply cut off in {place} {when}', 'High'),
        ('Overhead tank overflowing in {place}', 'High'),
        ('No drinking water available in {place}', 'High'),
        ('Water pipe burst in {place}', 'High'),
        ('Severe water leakage flooding {place}', 'High'),
        ('No hot water in {place} {when}', 'Medium'),
        ('Water pressure is very low in {place}', 'Medium'),
        ('Drain pipe blocked in {place}', 'Medium'),
        ('Washroom tap dripping constantly in {place}', 'Medium'),
        ('Flush is not working in {place} {when}', 'Medium'),
        ('Water cooler leaking in {place}', 'Medium'),
        ('Sewage smell coming from bathroom drain in {place}', 'Medium'),
        ('Water cooler near {place} is not working', 'Low'),
        ('Tap handle loose in {place}', 'Low'),
        ('Water filter cartridge needs cleaning in {place}', 'Low'),
        ('Drinking water dispenser knob broken in {place}', 'Low'),
    ],
    'Electricity': [
        ('Power cut in {place} {when}', 'High'),
        ('Sparks coming from the switch board in {place}', 'High'),
        ('Electric shock from socket in {place}', 'High'),
        ('Lights not working at all in {place} {when}', 'High'),
        ('Switchboard burnt and smoking in {place}', 'High'),
        ('No electricity in {place} {when}', 'High'),
        ('MCB tripping repeatedly in {place} {when}', 'High'),
        ('Exposed live wires hanging in {place}', 'High'),
        ('Ceiling fan wobbling dangerously in {place}', 'High'),
        ('Fan not running in {place} {when}', 'Medium'),
        ('AC unit not cooling in {place}', 'Medium'),
        ('Voltage fluctuation damaging appliances in {place}', 'Medium'),
        ('Extension board socket sparking in {place}', 'Medium'),
        ('Room heater not functioning in {place}', 'Medium'),
        ('Tube light in {place} needs replacing', 'Low'),
        ('Bulb fused in {place}', 'Low'),
        ('Street light outside {place} not working', 'Low'),
        ('Study lamp switch loose in {place}', 'Low'),
    ],
    'Wi-Fi': [
        ('Internet down completely across {place} {when}', 'High'),
        ('Cannot attend online exam due to wifi failure in {place}', 'High'),
        ('Wifi down during test submission in {place}', 'High'),
        ('Wi-Fi is not working in {place} {when}', 'Medium'),
        ('wifi nt working again in {place}', 'Medium'),
        ('No internet connectivity in {place} {when}', 'Medium'),
        ('Cannot connect to hostel wifi in {place} {when}', 'Medium'),
        ('Network drops every few minutes in {place}', 'Medium'),
        ('Hostel router offline in {place} {when}', 'Medium'),
        ('Wi-Fi login portal not opening in {place}', 'Medium'),
        ('Frequent wifi disconnection in {place}', 'Medium'),
        ('Wi-Fi speed is very slow in {place}', 'Low'),
        ('Wi-Fi signal weak in corner of {place}', 'Low'),
        ('Wi-Fi password reset needed for {place}', 'Low'),
        ('Slow upload speed in {place} {when}', 'Low'),
        ('LAN port loose in {place}', 'Low'),
    ],
    'Mess': [
        ('Cockroaches found in mess food {when}', 'High'),
        ('Food served in mess {when} was completely spoiled and sour', 'High'),
        ('Mess drinking water contaminated with dirt {when}', 'High'),
        ('Worms seen in rice at the mess {when}', 'High'),
        ('Unhygienic food causing stomach pain in mess {when}', 'High'),
        ('Mess closed abruptly without prior notice {when}', 'High'),
        ('Food served in the mess {when} was stale', 'Medium'),
        ('Mess food quality very poor {when}', 'Medium'),
        ('Food undercooked in the mess {when}', 'Medium'),
        ('Mess utensils are greasy and not washed {when}', 'Medium'),
        ('No drinking water available in mess hall {when}', 'Medium'),
        ('Mess staff handling food without gloves {when}', 'Medium'),
        ('Vegetables served in mess {when} were rotten', 'Medium'),
        ('Mess menu not followed today {when}', 'Low'),
        ('Long queue at mess breakfast counter {when}', 'Low'),
        ('Mess menu board outdated', 'Low'),
        ('Chairs in mess dining area sticky', 'Low'),
        ('Water jug missing from mess table {when}', 'Low'),
    ],
    'Cleanliness': [
        ('Stagnant sewage water overflowing in {place}', 'High'),
        ('Rats and pests infesting {place} {when}', 'High'),
        ('Washroom floor covered in filthy water in {place}', 'High'),
        ('Dead pest found in corridor near {place}', 'High'),
        ('Washroom tiles extremely slippery and hazardous in {place}', 'High'),
        ('Washroom in {place} is very dirty', 'Medium'),
        ('Garbage not collected from {place} {when}', 'Medium'),
        ('Foul smell spreading from washroom in {place}', 'Medium'),
        ('Dustbin overflowing with trash in {place}', 'Medium'),
        ('Corridor in {place} dirty and unwashed {when}', 'Medium'),
        ('Cleaning staff skipped sweeping in {place} {when}', 'Medium'),
        ('Bathroom drain choked with hair in {place}', 'Medium'),
        ('Toilet seat stained and unhygienic in {place}', 'Medium'),
        ('Dust on windows of {place}', 'Low'),
        ('Litter scattered around stairs near {place}', 'Low'),
        ('Mirror in washroom dirty near {place}', 'Low'),
        ('Spider webs in corner of {place}', 'Low'),
        ('Soap dispenser empty in {place}', 'Low'),
    ],
    'Furniture': [
        ('Bed frame collapsed completely in {place}', 'High'),
        ('Door lock jammed shut cannot enter room in {place}', 'High'),
        ('Main door latch broken in {place} security risk', 'High'),
        ('Bunk bed ladder broken in {place}', 'High'),
        ('Bed frame wooden plank cracked in {place}', 'Medium'),
        ('Study chair broken and unusable in {place}', 'Medium'),
        ('Bookshelf fell off wall in {place}', 'Medium'),
        ('Wardrobe door detached from hinges in {place}', 'Medium'),
        ('Window pane cracked and shaking in {place}', 'Medium'),
        ('Almirah lock jammed in {place}', 'Medium'),
        ('Desk drawer stuck unable to open in {place}', 'Medium'),
        ('Chair in {place} has a wobbly leg', 'Low'),
        ('Study table surface scratched in {place}', 'Low'),
        ('Curtain rod fallen down in {place}', 'Low'),
        ('Cupboard handle loose in {place}', 'Low'),
        ('Mattress cover torn in {place}', 'Low'),
        ('Shoe rack missing in {place}', 'Low'),
        ('Small stool cracked in {place}', 'Low'),
    ],
    'Other': [
        ('Fire extinguisher missing from {place}', 'High'),
        ('Security guard absent from gate near {place} {when}', 'High'),
        ('Lift stuck between floors near {place} {when}', 'High'),
        ('Emergency exit door locked in {place}', 'High'),
        ('First aid box empty in {place}', 'High'),
        ('CCTV camera facing {place} is dead', 'High'),
        ('Loud music disturbance in {place} {when}', 'Medium'),
        ('Stray dogs entered hostel near {place}', 'Medium'),
        ('Gym equipment cable broken near {place}', 'Medium'),
        ('Common room air cooler leaking in {place}', 'Medium'),
        ('Corridor light switch broken in {place}', 'Medium'),
        ('Please add a notice board near {place}', 'Low'),
        ('No parking space for cycles near {place}', 'Low'),
        ('Common room TV remote missing {when}', 'Low'),
        ('Request for newspaper in common room {place}', 'Low'),
        ('Lost and found box needed near {place}', 'Low'),
        ('Ironing board missing in laundry room near {place}', 'Low'),
        ('Clock stopped working in common room {place}', 'Low'),
    ],
}


def _generate_category_samples(category, templates, rng, target_count=50):
    """Generate diverse unique samples, ensuring every template is included."""
    samples = []
    seen = set()

    # Pass 1: Ensure every template appears at least once
    for i, (tmpl, priority) in enumerate(templates):
        p = PLACES[i % len(PLACES)]
        w = TIMES[i % len(TIMES)]
        text = tmpl.format(place=p, when=w)
        if text not in seen:
            seen.add(text)
            samples.append({'text': text, 'category': category, 'priority': priority})

    # Pass 2: Round-robin across templates to reach target_count
    cycle = 1
    while len(samples) < target_count:
        for i, (tmpl, priority) in enumerate(templates):
            if len(samples) >= target_count:
                break
            p = PLACES[(i * 3 + cycle) % len(PLACES)]
            w = TIMES[(i * 2 + cycle) % len(TIMES)]
            text = tmpl.format(place=p, when=w)
            if text not in seen:
                seen.add(text)
                samples.append({
                    'text': text,
                    'category': category,
                    'priority': priority,
                })
        cycle += 1

    return samples


def generate(output_path=None, target_per_category=50):
    """Generate the synthetic dataset deterministically and write to CSV.

    Produces ~350 samples (target_per_category * 7 categories) with:
    - Balanced priorities
    - Every template represented
    - No duplicate descriptions
    - No empty descriptions
    - Local random.Random(42) instance (does not pollute global random state)
    """
    rng = random.Random(42)

    if output_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(here, 'data', 'complaints.csv')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    all_rows = []
    for category in CATEGORIES:
        cat_samples = _generate_category_samples(
            category, TEMPLATES[category], rng, target_count=target_per_category
        )
        all_rows.extend(cat_samples)

    # Final deterministic shuffle
    rng.shuffle(all_rows)

    df = pd.DataFrame(all_rows, columns=['text', 'category', 'priority'])
    # Assert deduplication
    df = df.drop_duplicates(subset=['text']).reset_index(drop=True)

    df.to_csv(output_path, index=False)
    print(
        f"Generated {len(df)} rows across "
        f"{df['category'].nunique()} categories -> {output_path}"
    )
    for cat in CATEGORIES:
        sub = df[df['category'] == cat]
        print(f"  {cat}: {len(sub)} samples ({dict(sub['priority'].value_counts())})")

    return df


if __name__ == '__main__':
    generate()
