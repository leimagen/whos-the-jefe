const EMPLOYEE_NAMES = {
  "emp_001": "Maria",
  "emp_002": "James",
  "emp_003": "Lu"
};

const REMOTE_EMPLOYEES = ["emp_003"];

const STATUS_POS_Y_WORKING = 175;
const STATUS_POS_Y_FOCUSED = 175;
const STATUS_POS_Y_DISTRACTED = 215;
const STATUS_POS_Y_MEETING = 105;
const STATUS_POS_Y_BREAK = 335;
const STATUS_POS_Y_CHATTING = 235;

// Presential positions
const PRESENTIAL_POSITIONS = {
  "working":                  { "emp_001": {x:200,y:STATUS_POS_Y_WORKING}, "emp_002": {x:400,y:STATUS_POS_Y_WORKING} },
  "focused":                  { "emp_001": {x:200,y:STATUS_POS_Y_FOCUSED}, "emp_002": {x:400,y:STATUS_POS_Y_FOCUSED} },
  "distracted":               { "emp_001": {x:230,y:STATUS_POS_Y_DISTRACTED}, "emp_002": {x:430,y:STATUS_POS_Y_DISTRACTED} },
  "in a meeting":             { "emp_001": {x:590,y:STATUS_POS_Y_MEETING},  "emp_002": {x:650,y:STATUS_POS_Y_MEETING}  },
  "on a break":               { "emp_001": {x:620,y:STATUS_POS_Y_BREAK}, "emp_002": {x:680,y:STATUS_POS_Y_BREAK} },
  "chatting with a coworker": { "emp_001": {x:290,y:STATUS_POS_Y_CHATTING}, "emp_002": {x:350,y:STATUS_POS_Y_CHATTING} }
};

// Remote zone positions — fixed slots inside the remote box
const REMOTE_POSITIONS = {
  "emp_003": {x: 105, y: 350}
};

export function initLabels() {
  setInterval(pollLabels, 3000);
  setInterval(pollReactions, 4000);
  pollLabels();
}

function pollLabels() {
  fetch("/simulator/state.json")
    .then(r => r.json())
    .then(state => {
      document.getElementById("hud-day").textContent = `Day ${state.agency.day}`;
      document.getElementById("hud-agency").textContent = state.agency.name || "Your Agency";
      updateEmployeeLabels(state.employees);
    })
    .catch(() => {});
}

function pollReactions() {
  fetch("http://localhost:3001/api/reactions")
    .then(r => r.json())
    .then(reactions => {
      reactions.forEach(r => {
        // Duration of dialog bubble on screen
        const duration = r.is_conversation ? 8000 : 14000;
        showThoughtBubble(r.employee_id, r.reaction, r.reaction_type || "thought", duration);
      });
    })
    .catch(() => {});
}

setInterval(pollReactions, 4000);

function updateEmployeeLabels(employees) {
  const overlay = document.getElementById("office-overlay");

  employees.forEach(emp => {
    const isRemote = REMOTE_EMPLOYEES.includes(emp.id);
    const activity = emp.current_activity || "working";

    let pos;
    if (isRemote) {
      pos = REMOTE_POSITIONS[emp.id];
    } else {
      pos = PRESENTIAL_POSITIONS[activity]?.[emp.id];
    }
    if (!pos) return;

    let label = document.getElementById(`label-${emp.id}`);
    if (!label) {
        label = document.createElement("div");
        label.id = `label-${emp.id}`;
        label.className = "emp-label";
        label.innerHTML = `
            <div class="emp-name">${EMPLOYEE_NAMES[emp.id] || emp.id}</div>
            <div class="emp-activity" id="act-${emp.id}"></div>
            ${isRemote ? '<div class="emp-remote-tag">🌐 remote</div>' : ''}
        `;
        label.addEventListener("mouseenter", () => {
            label.style.opacity = "1";
        });
        label.addEventListener("mouseleave", () => {
            label.style.opacity = "0";
        });
        overlay.appendChild(label);
    }

    label.style.left = pos.x + "px";
    label.style.top = pos.y + "px";
    document.getElementById(`act-${emp.id}`).textContent = activity;
  });
}

export function showThoughtBubble(employeeId, text, type = "thought", duration = 10000) {
  const overlay = document.getElementById("office-overlay");

  const existing = document.getElementById(`bubble-${employeeId}`);
  if (existing) existing.remove();

  const label = document.getElementById(`label-${employeeId}`);
  if (!label) return;

  const x = parseFloat(label.style.left);
  const y = parseFloat(label.style.top);

  const bubble = document.createElement("div");
  bubble.id = `bubble-${employeeId}`;
  bubble.className = type === "spoken" ? "speech-bubble" : "thought-bubble";
  bubble.textContent = text;
  bubble.style.left = x + "px";
  bubble.style.bottom = (600 - y + 20) + "px"; // anchor from bottom
  bubble.style.top = "auto";

  overlay.appendChild(bubble);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      bubble.classList.add("visible");
    });
  });

  setTimeout(() => {
    bubble.classList.remove("visible");
    setTimeout(() => bubble.remove(), 200);
  }, duration);
}