import { showThoughtBubble } from '/frontend/js/labels.js';

let emails = [];
let currentEmailId = null;

export function initInbox() {
  document.getElementById("inbox-btn").onclick = () => {
    document.getElementById("inbox-panel").classList.toggle("open");
  };
  document.getElementById("close-inbox").onclick = () => {
    document.getElementById("inbox-panel").classList.remove("open");
    document.getElementById("email-detail").classList.remove("open");
  };
  document.getElementById("close-detail").onclick = () => {
    document.getElementById("email-detail").classList.remove("open");
  };
  document.getElementById("send-reply").onclick = sendReply;

  setInterval(loadEmails, 5000);
  loadEmails();
}

function loadEmails() {
  fetch("/simulator/inbox.json")
    .then(r => r.json())
    .then(data => {
      emails = data;
      renderEmailList();
      updateUnreadBadge();
    })
    .catch(() => {});
}

function updateUnreadBadge() {
  const unread = emails.filter(e => !e.read).length;
  const badge = document.getElementById("unread-count");
  const btn = document.getElementById("inbox-btn");
  if (unread > 0) {
    badge.textContent = unread;
    badge.style.display = "inline-block";
    btn.classList.add("has-unread");
  } else {
    badge.style.display = "none";
    btn.classList.remove("has-unread");
  }
}

function renderEmailList() {
  const list = document.getElementById("email-list");
  list.innerHTML = "";
  [...emails].reverse().forEach(email => {
    const statusClass = email.replied ? "replied" : (email.read ? "read" : "unread");
    const div = document.createElement("div");
    div.className = `email-item ${statusClass}`;
    div.innerHTML = `
      <div class="sender">${email.from}</div>
      <div class="subject">${email.subject}</div>
      <div class="preview">${email.body.substring(0, 60)}...</div>
      <div class="meta">
        <span>Day ${email.day}</span>
        ${email.replied ? '<span class="replied-tag">✓ Replied</span>' : ''}
      </div>
    `;
    div.onclick = () => openEmail(email.id);
    list.appendChild(div);
  });
}

function openEmail(id) {
  const email = emails.find(e => e.id === id);
  if (!email) return;
  currentEmailId = id;

  document.getElementById("detail-sender").textContent = email.from;
  document.getElementById("detail-subject").textContent = email.subject;
  document.getElementById("detail-day").textContent = `Day ${email.day}`;
  document.getElementById("detail-body").textContent = email.body;
  document.getElementById("reply-text").value = "";
  document.getElementById("reply-status").style.display = "none";
  document.getElementById("send-reply").disabled = email.replied || false;
  document.getElementById("email-detail").classList.add("open");

  email.read = true;
  saveInbox();
  renderEmailList();
  updateUnreadBadge();
}

function saveInbox() {
  fetch("http://localhost:3001/api/inbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(emails)
  }).catch(() => {});
}

function sendReply() {
  const text = document.getElementById("reply-text").value.trim();
  if (!text || !currentEmailId) return;

  const email = emails.find(e => e.id === currentEmailId);
  document.getElementById("send-reply").disabled = true;

  // Clear textarea immediately on click
  document.getElementById("reply-text").value = "";

  fetch("http://localhost:3001/api/reply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email_id: currentEmailId,
      employee_id: email.employee_id,
      reply: text
    })
  })
  .then(r => r.json())
  .then(() => {
    email.replied = true;
    // Show reaction bubble on the employee's sprite
    const empId = email.employee_id;
    showThoughtBubble(empId, "📨 Got your message...");
    saveInbox();
    renderEmailList();

    // Show green status immediately
    const status = document.getElementById("reply-status");
    status.style.display = "block";

    // After 1 second, slide panel out and hide
    setTimeout(() => {
      const detail = document.getElementById("email-detail");
      detail.style.transition = "transform 0.3s ease, opacity 0.3s ease";
      detail.style.transform = "translateX(100%)";
      detail.style.opacity = "0";
      setTimeout(() => {
        detail.classList.remove("open");
        detail.style.transform = "";
        detail.style.opacity = "";
        detail.style.transition = "";
        status.style.display = "none";
      }, 300);
    }, 1000);
  })
  .catch(() => {
    document.getElementById("send-reply").disabled = false;
    document.getElementById("reply-text").value = text; // restore if failed
  });
}