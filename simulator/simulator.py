import os
import json
import time
import random
from dotenv import load_dotenv
import anthropic
from agent import Employee, load_state, save_state, get_employee, update_employee

CONTRACTS_FILE = "simulator/contracts.json"

def load_contracts():
    if not os.path.exists(CONTRACTS_FILE):
        return {"available": [], "active": [], "completed": []}
    with open(CONTRACTS_FILE) as f:
        return json.load(f)

def save_contracts(contracts):
    with open(CONTRACTS_FILE, "w") as f:
        json.dump(contracts, f, indent=2)

last_email_tick = {}

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TICK_INTERVAL = 5  # seconds between ticks (will be much longer in real gameplay)

ACTIVITIES = [
    "working",
    "working",
    "focused",
    "on a break",
    "in a meeting",
    "distracted"
    "chatting with a coworker"
]

def advance_day(state):
    state["agency"]["day"] += 1
    current_day = state["agency"]["day"]
    print(f"\n=== DAY {current_day} BEGINS ===\n")

    for emp_data in state["employees"]:
        emp_data["energy"] = 100
        emp_data["next_activity_tick"] = 0  # reset so everyone is active again
        if emp_data["mood"] == "frustrated" and random.random() < 0.3:
            emp_data["mood"] = "neutral"
            print(f"[MOOD] {emp_data['name']} seems to have calmed down overnight.")

    # Check contract expiration
    contracts = load_contracts()
    expired = [c for c in contracts["available"] if c["expires_day"] <= current_day]
    if expired:
        for c in expired:
            print(f"[CONTRACT] Expired: {c['client']} — {c['description'][:40]}...")
        contracts["available"] = [c for c in contracts["available"] if c["expires_day"] > current_day]
        save_contracts(contracts)

    save_state(state)

def simulate_tick(state, current_tick):
    print(f"\n--- Tick | Day {state['agency']['day']} ---")

    # Reset in_conversation flags at start of each tick
    for emp_data in state["employees"]:
        emp_data["in_conversation"] = False

    for emp_data in state["employees"]:
        emp = Employee(emp_data)

        # Each employee changes on their own schedule
        next_tick = emp_data.get("next_activity_tick", 0)
        if current_tick >= next_tick:
            new_activity = random.choice(ACTIVITIES)
            if new_activity != emp.current_activity:
                emp_data["current_activity"] = new_activity
                print(f"[ACTIVITY] {emp.name} is now: {new_activity}")
            emp_data["next_activity_tick"] = current_tick + random.randint(1, 4)

        # Energy drains over time
        new_energy = max(0, emp_data["energy"] - random.randint(5, 15))
        emp_data["energy"] = new_energy

        # If energy is very low, mood gets worse
        if new_energy < 20 and emp_data["mood"] == "neutral":
            emp_data["mood"] = "tired"
            print(f"[MOOD] {emp.name} is exhausted.")

        # Check if something noteworthy happened
        should_email = check_for_event(emp, state, current_tick)
        if should_email:
            last_email_tick[emp.id] = current_tick
            generate_email_event(emp, state)

        # Conversations
        if emp_data.get("current_activity") == "chatting with a coworker" and not emp_data.get("in_conversation", False):
            others = [e for e in state["employees"]
                      if e["id"] != emp_data["id"]
                      and e.get("current_activity") in ["chatting with a coworker", "working", "focused"]
                      and not e.get("in_conversation", False)]

            if others:
                partner = random.choice(others)
                convo_key = f"last_convo_{'_'.join(sorted([emp_data['id'], partner['id']]))}"
                last_convo = state["agency"].get(convo_key, -99)

                if current_tick - last_convo >= 10:
                    emp_data["in_conversation"] = True
                    partner["in_conversation"] = True
                    state["agency"][convo_key] = current_tick
                    save_state(state)
                    simulate_conversation(emp_data, partner, state)
                    emp_data["in_conversation"] = False
                    partner["in_conversation"] = False

    save_state(state)

def check_for_event(emp, state, current_tick):
    base_chance = 0.02

    if emp.mood in ["frustrated", "tired", "angry"]:
        base_chance += 0.2

    if emp.energy < 30:
        base_chance += 0.1

    # Cooldown — no emails within 3 ticks of the last one
    last = last_email_tick.get(emp.id, -99)
    if current_tick - last < 8:
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

def simulate_conversation(emp_a_data, emp_b_data, state):
    """Two employees have a real conversation that affects their relationship."""

    def send_chat_bubble(employee_id, text):
        try:
            import urllib.request
            data = json.dumps({
                "employee_id": employee_id,
                "reaction": text,
                "reaction_type": "spoken",
                "is_conversation": True
            }).encode()
            req = urllib.request.Request(
                "http://localhost:3001/api/reaction",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req)
        except:
            pass

    emp_a = Employee(emp_a_data)
    emp_b = Employee(emp_b_data)
    agency = state["agency"]

    print(f"\n💬 CONVERSATION: {emp_a.name} & {emp_b.name}")
    print("-" * 40)

    relationship_ab = emp_a_data.get("relationship_with_coworkers", {}).get(emp_b_data["id"], 50)
    relationship_ba = emp_b_data.get("relationship_with_coworkers", {}).get(emp_a_data["id"], 50)

    conversation_history = []
    
    # A opens the conversation
    opener_prompt = f"""You are {emp_a.name}, a {emp_a.role} at a boutique design agency called '{agency['name']}'.
    Your traits: {', '.join(emp_a.traits)}.
    Your nationality: {emp_a.nationality}.
    Your mood: {emp_a.mood}.
    Your relationship with {emp_b.name} ({emp_b.role}): {relationship_ab}/100.
    It is day {agency['day']}.

    You just started chatting with {emp_b.name}. Start a natural, casual conversation.
    Start a casual, natural conversation — NOT about work. Talk about hobbies, weekend plans, food, music, travel, opinions, anything personal.
    Keep it to ONE short sentence max. Be yourself, be casual."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": opener_prompt}]
    )
    opener = msg.content[0].text.strip()
    conversation_history.append({"speaker": emp_a.name, "text": opener})
    print(f"  {emp_a.name}: {opener}")

    send_chat_bubble(emp_a_data["id"], opener)
    time.sleep(3)  # pause between bubbles so they don't overlap

    # 2 exchanges back and forth
    current_speaker = emp_b
    current_speaker_data = emp_b_data
    other_speaker = emp_a
    other_speaker_data = emp_a_data

    for i in range(3):
        history_text = "\n".join([f"{m['speaker']}: {m['text']}" for m in conversation_history])
        
        reply_prompt = f"""You are {current_speaker.name}, a {current_speaker.role} at a boutique design agency called '{agency['name']}'.
        Your traits: {', '.join(current_speaker.traits)}.
        Your nationality: {current_speaker.nationality}.
        Your mood: {current_speaker.mood}.
        Your relationship with {other_speaker.name}: {relationship_ba if i == 0 else relationship_ab}/100.

        Conversation so far:
        {history_text}

        Reply in ONE short casual sentence. Keep it personal, not work-related. Stay in character."""

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": reply_prompt}]
        )
        reply = msg.content[0].text.strip()
        conversation_history.append({"speaker": current_speaker.name, "text": reply})
        print(f"  {current_speaker.name}: {reply}")

        send_chat_bubble(current_speaker_data["id"], reply)
        time.sleep(3)

        # Swap speakers
        current_speaker, other_speaker = other_speaker, current_speaker
        current_speaker_data, other_speaker_data = other_speaker_data, current_speaker_data
        relationship_ab, relationship_ba = relationship_ba, relationship_ab

    # Evaluate impact — how did the conversation go?
    full_convo = "\n".join([f"{m['speaker']}: {m['text']}" for m in conversation_history])
    
    eval_prompt = f"""Here is a conversation between two coworkers:
    {full_convo}

    Evaluate the impact of this conversation on their relationship and mood.
    Respond ONLY with raw JSON, no markdown:
    {{"relationship_delta_ab": 0, "relationship_delta_ba": 0, "mood_a": "neutral", "mood_b": "neutral"}}

    relationship_delta values: -10 to +10
    mood values: neutral, happy, motivated, frustrated, angry, anxious, tired"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": eval_prompt}]
    )
    
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        impact = json.loads(raw)
        
        # Update relationship A → B
        coworkers_a = emp_a_data.get("relationship_with_coworkers", {})
        coworkers_a[emp_b_data["id"]] = max(0, min(100, relationship_ab + impact.get("relationship_delta_ab", 0)))
        update_employee(state, emp_a_data["id"], {
            "relationship_with_coworkers": coworkers_a,
            "mood": impact.get("mood_a", emp_a.mood)
        })

        # Update relationship B → A
        coworkers_b = emp_b_data.get("relationship_with_coworkers", {})
        coworkers_b[emp_a_data["id"]] = max(0, min(100, relationship_ba + impact.get("relationship_delta_ba", 0)))
        update_employee(state, emp_b_data["id"], {
            "relationship_with_coworkers": coworkers_b,
            "mood": impact.get("mood_b", emp_b.mood)
        })

        print(f"  → Relationship impact: {impact.get('relationship_delta_ab', 0):+d} / {impact.get('relationship_delta_ba', 0):+d}")
        print(f"  → Moods after: {emp_a.name}={impact.get('mood_a')} | {emp_b.name}={impact.get('mood_b')}")

    except Exception as e:
        print(f"  [ERROR] Could not evaluate conversation: {e}")

    print("-" * 40)

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
    {{"mood": "one of: neutral, happy, motivated, frustrated, angry, anxious, tired", "relationship_delta": 0, "reaction": "max 15 words in first person", "reaction_type": "thought or spoken"}}

    Use "thought" when the reaction is internal — something you wouldn't say out loud.
    Use "spoken" when the reaction is something you'd actually say directly to your boss."""

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
        reaction_type = response.get("reaction_type", "thought")

        new_relationship = max(0, min(100, emp.relationship_with_boss + delta))

        update_employee(state, emp.id, {
            "mood": new_mood,
            "relationship_with_boss": new_relationship
        })

        print(f"\n💬 {emp.name} reacts to your reply:")
        print(f"   \"{reaction}\"")
        print(f"   Type: {reaction_type}")
        print(f"   Mood: {emp.mood} → {new_mood}")
        print(f"   Relationship: {emp.relationship_with_boss} → {new_relationship}")

        # Send reaction to frontend
        try:
            import urllib.request
            reaction_data = json.dumps({
                "employee_id": emp.id,
                "reaction": reaction,
                "reaction_type": reaction_type
            }).encode()
            req = urllib.request.Request(
                "http://localhost:3001/api/reaction",
                data=reaction_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req)
        except:
            pass

    except Exception as e:
        print(f"[ERROR] Could not parse reaction for {emp.name}: {e}")
        print(f"[DEBUG] Raw response: {raw}")

    # Always clear the processed reply
    with open("simulator/replies.json", "w") as f:
        json.dump(remaining, f, indent=2)

def run_simulator():
    print("Who's The Jefe — Simulator starting...\n")
    state = load_state()
    ticks_per_day = 8
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