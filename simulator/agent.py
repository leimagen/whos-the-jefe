import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

STATE_FILE = "simulator/state.json"

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_employee(state, employee_id):
    for emp in state["employees"]:
        if emp["id"] == employee_id:
            return emp
    return None

def update_employee(state, employee_id, updates):
    for emp in state["employees"]:
        if emp["id"] == employee_id:
            emp.update(updates)
    save_state(state)


class Employee:
    def __init__(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.role = data["role"]
        self.skill_level = data["skill_level"]
        self.traits = data["traits"]
        self.nationality = data["nationality"]
        self.mood = data["mood"]
        self.energy = data["energy"]
        self.salary = data["salary"]
        self.is_remote = data["is_remote"]
        self.relationship_with_boss = data["relationship_with_boss"]
        self.current_activity = data["current_activity"]

    def think(self, situation):
        prompt = f"""You are {self.name}, a {self.role} at a boutique design agency.
        Your skill level is {self.skill_level}/10.
        Your personality traits are: {', '.join(self.traits)}.
        Your nationality is: {self.nationality}.
        Your current mood is: {self.mood}.
        Your energy level is: {self.energy}/100.
        Your relationship with your boss is: {self.relationship_with_boss}/100.

        Situation: {situation}

        Respond in first person, in English, in 3 sentences max, as this character would react."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def update_mood(self, new_mood, state):
        self.mood = new_mood
        update_employee(state, self.id, {"mood": new_mood})
        print(f"[STATE] {self.name}'s mood updated to: {new_mood}")


# Basic test
if __name__ == "__main__":
    state = load_state()
    agency = state["agency"]

    print(f"--- {agency['name']} | Day {agency['day']} | Budget: ${agency['budget']} ---\n")

    emp_data = get_employee(state, "emp_001")
    maria = Employee(emp_data)

    response = maria.think("The client rejected your logo proposal without any explanation.")
    print(f"{maria.name}: {response}\n")

    # Update her mood after the bad news
    maria.update_mood("frustrated", state)

    # She thinks again now that she's frustrated
    response2 = maria.think("Your boss just asked how the project is going.")
    print(f"{maria.name} (frustrated): {response2}")

def get_available_contracts(state, contracts):
    """Returns contracts the agency can currently take based on team skills."""
    team_roles = [emp["role"] for emp in state["employees"]]
    takeable = []

    for contract in contracts["available"]:
        reputation = state["agency"].get("reputation", 0)
        if reputation < contract["reputation_required"]:
            continue

        can_fill = all(
            any(role in emp_role for emp_role in team_roles)
            for role in contract["required_roles"]
        )

        takeable.append({
            **contract,
            "can_take": can_fill
        })

    return takeable