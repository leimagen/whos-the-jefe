const EMPLOYEE_NAMES = {
  "emp_001": "Maria",
  "emp_002": "James",
  "emp_003": "Lu"
};

const REMOTE_EMPLOYEES = ["emp_003"];

// Presential positions
const PRESENTIAL_POSITIONS = {
  "working":                  { "emp_001": {x:200,y:285}, "emp_002": {x:400,y:285} },
  "focused":                  { "emp_001": {x:200,y:285}, "emp_002": {x:400,y:285} },
  "distracted":               { "emp_001": {x:230,y:325}, "emp_002": {x:430,y:325} },
  "in a meeting":             { "emp_001": {x:590,y:215}, "emp_002": {x:650,y:215} },
  "on a break":               { "emp_001": {x:620,y:445}, "emp_002": {x:680,y:445} },
  "chatting with a coworker": { "emp_001": {x:290,y:345}, "emp_002": {x:350,y:345} }
};

// Remote zone positions — fixed slots inside the remote box
const REMOTE_POSITIONS = {
  "emp_003": {x: 105, y: 470}
};

export function initLabels() {
  setInterval(pollLabels, 3000);
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
      overlay.appendChild(label);
    }

    label.style.left = pos.x + "px";
    label.style.top = pos.y + "px";
    document.getElementById(`act-${emp.id}`).textContent = activity;
  });
}