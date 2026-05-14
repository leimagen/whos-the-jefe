import os
import json
import time
import random
from dotenv import load_dotenv
import anthropic
from agent import Employee, load_state, save_state, get_employee, update_employee

last_email_tick = {}

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TICK_INTERVAL = 30  # seconds between ticks (will be much longer in real gameplay)

ACTIVITIES = [
    "working",
    "on a break",
    "in a meeting",
    "chatting with a coworker",
    "distracted",
    "focused"
]

def advance_day(state):
    state["agency"]["day"] += 1
    print(f"\n=== DAY {state['agency']['day']} BEGINS ===\n")

    for emp_data in state["employees"]:
        # Energy resets each day
        emp_data["energy"] = 100

        # Mood has a chance to shift slightly
        if emp_data["mood"] == "frustrated" and random.random() < 0.3:
            emp_data["mood"] = "neutral"
            print(f"[MOOD] {emp_data['name']} seems to have calmed down overnight.")

    save_state(state)

def simulate_tick(state, current_tick):
    print(f"\n--- Tick | Day {state['agency']['day']} ---")

    for emp_data in state["employees"]:
        emp = Employee(emp_data)

        # Random activity change
        new_activity = random.choice(ACTIVITIES)
        if new_activity != emp.current_activity:
            update_employee(state, emp.id, {"current_activity": new_activity})
            print(f"[ACTIVITY] {emp.name} is now: {new_activity}")

        # Energy drains over time
        new_energy = max(0, emp_data["energy"] - random.randint(5, 15))
        update_employee(state, emp.id, {"energy": new_energy})

        # If energy is very low, mood gets worse
        if new_energy < 20 and emp_data["mood"] == "neutral":
            update_employee(state, emp.id, {"mood": "tired"})
            print(f"[MOOD] {emp.name} is exhausted.")

        # Check if something noteworthy happened
        should_email = check_for_event(emp, state, current_tick)
        if should_email:
            last_email_tick[emp.id] = current_tick
            generate_email_event(emp, state)

    save_state(state)

def check_for_event(emp, state, current_tick):
    base_chance = 0.05

    if emp.mood in ["frustrated", "tired", "angry"]:
        base_chance += 0.2

    if emp.energy < 30:
        base_chance += 0.1

    # Cooldown — no emails within 3 ticks of the last one
    last = last_email_tick.get(emp.id, -99)
    if current_tick - last < 3:
        return False

    return random.random() < base_chance

def generate_email_event(emp, state):
    agency = state["agency"]

    # Build coworker context
    coworker_context = ""
    for other in state["employees"]:
        if other["id"] != emp.id:
            relationship = 50
            coworker_context += f"- {other['name']} ({other['role']}): relationship {relationship}/100, their mood is {other['mood']}\n"

    prompt = f"""You are {emp.name}, a {emp.role} at '{agency['name']}', a boutique design agency.
    Your traits: {', '.join(emp.traits)}.
    Your nationality: {emp.nationality}.
    Your mood: {emp.mood}.
    Your energy: {emp.energy}/100.
    Your relationship with your boss: {emp.relationship_with_boss}/100.
    Your current activity: {emp.current_activity}.
    It is day {agency['day']} at the agency.

    Your coworkers:
    {coworker_context}
    Write a short work email to your boss that reflects your current situation.
    Your personality should come through clearly in your writing style.
    It can be about work, a coworker, a concern, or a request — whatever feels natural given your state.
    Include a subject line.
    Keep it under 100 words."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )

    email_text = message.content[0].text

    # Parse subject and body
    lines = email_text.strip().split("\n")
    subject = lines[0].replace("**Subject:", "").replace("Subject:", "").replace("**", "").strip()
    body = "\n".join(lines[1:]).strip()

    # Save to inbox
    inbox = []
    if os.path.exists("simulator/inbox.json"):
        with open("simulator/inbox.json") as f:
            inbox = json.load(f)

    inbox.append({
        "id": f"email_{len(inbox)+1}",
        "employee_id": emp.id,
        "from": f"{emp.name} <{emp.role}>",
        "subject": subject,
        "body": body,
        "day": state["agency"]["day"],
        "read": False
    })

    with open("simulator/inbox.json", "w") as f:
        json.dump(inbox, f, indent=2)

    print(f"\n📧 EMAIL FROM {emp.name.upper()} saved to inbox.")

def process_replies(state):
    if not os.path.exists("simulator/replies.json"):
        return

    with open("simulator/replies.json") as f:
        replies = json.load(f)

    if not replies:
        return

    # Take only the first reply and process it
    reply = replies[0]
    remaining = replies[1:]

    emp_data = get_employee(state, reply["employee_id"])
    if not emp_data:
        with open("simulator/replies.json", "w") as f:
            json.dump(remaining, f, indent=2)
        return

    emp = Employee(emp_data)

    prompt = f"""You are {emp.name}, a {emp.role} at a boutique design agency.
Your traits: {', '.join(emp.traits)}.
Your current mood: {emp.mood}.
Your relationship with your boss: {emp.relationship_with_boss}/100.

Your boss just replied to your email with this message:
\"{reply['reply']}\"

Respond with ONLY a raw JSON object, no markdown, no backticks, no explanation:
{{"mood": "one of: neutral, happy, motivated, frustrated, angry, anxious, tired", "relationship_delta": 0, "reaction": "one sentence"}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip markdown backticks if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        response = json.loads(raw)
        new_mood = response.get("mood", emp.mood)
        delta = int(response.get("relationship_delta", 0))
        reaction = response.get("reaction", "")

        new_relationship = max(0, min(100, emp.relationship_with_boss + delta))

        update_employee(state, emp.id, {
            "mood": new_mood,
            "relationship_with_boss": new_relationship
        })

        print(f"\n💬 {emp.name} reacts to your reply:")
        print(f"   \"{reaction}\"")
        print(f"   Mood: {emp.mood} → {new_mood}")
        print(f"   Relationship: {emp.relationship_with_boss} → {new_relationship}")

    except Exception as e:
        print(f"[ERROR] Could not parse reaction for {emp.name}: {e}")
        print(f"[DEBUG] Raw response: {raw}")

    # Always clear the processed reply
    with open("simulator/replies.json", "w") as f:
        json.dump(remaining, f, indent=2)

def run_simulator():
    print("Who's The Jefe — Simulator starting...\n")
    state = load_state()
    ticks_per_day = 5
    tick_count = 0
    total_ticks = 0

    try:
        while True:
            state = load_state()
            simulate_tick(state, total_ticks)
            total_ticks += 1
            tick_count += 1

            if tick_count >= ticks_per_day:
                tick_count = 0
                advance_day(state)

            process_replies(state)
            time.sleep(TICK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nSimulator stopped.")

if __name__ == "__main__":
    run_simulator()