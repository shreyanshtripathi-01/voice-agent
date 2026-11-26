/* Browser UI: speech in (Web Speech API), speech out (speechSynthesis), live dashboards. */
const $ = (id) => document.getElementById(id);

let sid = null;
let listening = false;
let recognition = null;
let selectedSlot = null;
let demoRunning = false;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(path, method = "GET", body = null) {
  const options = { method, headers: { "Content-Type": "application/json" } };
  if (body) options.body = JSON.stringify(body);
  try {
    const res = await fetch(path, options);
    return await res.json();
  } catch (err) {
    return { ok: false, error: "Cannot reach the server. Is app.py running?" };
  }
}

function addBubble(role, text, extra = "") {
  const el = document.createElement("div");
  el.className = `bubble ${role} ${extra}`.trim();
  const who = document.createElement("span");
  who.className = "who";
  who.textContent = role === "user" ? "Prospect" : "Ava · AI agent";
  const content = document.createElement("span");
  content.textContent = text;
  el.append(who, content);
  $("transcript").append(el);
  $("transcript").scrollTop = $("transcript").scrollHeight;
  return el;
}

function speak(text, lang) {
  if (!$("ttsToggle").checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text.replace(/[*_#>]/g, ""));
  utterance.lang = lang || "en-IN";
  utterance.rate = 1.02;
  const voices = window.speechSynthesis.getVoices();
  const match = voices.find((v) => v.lang.toLowerCase().startsWith(utterance.lang.slice(0, 2).toLowerCase()));
  if (match) utterance.voice = match;
  window.speechSynthesis.speak(utterance);
}

function resetPanels() {
  $("gradeBadge").textContent = "—";
  $("gradeBadge").className = "grade";
  $("leadName").textContent = "Waiting for caller";
  $("scoreText").textContent = "0 / 100";
  $("scoreFill").style.width = "0%";
  for (const key of ["budget", "authority", "need", "timeline"]) {
    $(key + "Fill").style.width = "0%";
    $(key + "Val").textContent = "0";
  }
  $("slotChips").innerHTML = '<span class="chip empty">No details yet</span>';
  $("sentimentTag").textContent = "neutral";
  $("sparkLine").setAttribute("points", "");
  $("sources").innerHTML = '<p class="muted small">No lookups yet — ask about pricing, languages or security.</p>';
  $("appointment").textContent = "Not booked yet";
  $("appointment").className = "appointment";
  $("slotOptions").innerHTML = "";
  $("bookBtn").disabled = true;
  $("stageBadge").textContent = "Ready";
  $("summaryCard").hidden = true;
  selectedSlot = null;
}

async function startCall(lang) {
  const result = await api("/api/session", "POST", { lang: lang || $("langSelect").value });
  if (!result.ok) return result;
  sid = result.session_id;
  selectedSlot = null;
  $("transcript").innerHTML = "";
  resetPanels();
  $("stageBadge").textContent = "GREETING";
  addBubble("agent", result.message);
  speak(result.message, result.language);
  return result;
}

function updatePanels(r) {
  const q = r.qualification || { total: 0, grade: "—", parts: {} };
  $("gradeBadge").textContent = q.grade;
  $("gradeBadge").className = "grade " + q.grade;
  $("leadName").textContent = r.slots?.name || "Prospect";
  $("scoreText").textContent = `${q.total} / 100`;
  $("scoreFill").style.width = q.total + "%";
  for (const key of ["budget", "authority", "need", "timeline"]) {
    const value = q.parts?.[key] || 0;
    $(key + "Fill").style.width = value * 4 + "%";
    $(key + "Val").textContent = value;
  }
  $("stageBadge").textContent = r.stage;

  const chips = [];
  const s = r.slots || {};
  if (s.name) chips.push("Name: " + s.name);
  if (s.company) chips.push("Company: " + s.company);
  if (s.role) chips.push("Role: " + s.role);
  if (s.need) chips.push("Need: " + s.need);
  if (s.budget_text) chips.push("Budget: " + s.budget_text);
  if (s.timeline_text) chips.push("Timeline: " + s.timeline_text);
  if (s.authority) chips.push("Authority: " + s.authority);
  $("slotChips").innerHTML = "";
  if (!chips.length) {
    $("slotChips").innerHTML = '<span class="chip empty">No details yet</span>';
  } else {
    chips.forEach((text) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = text;
      $("slotChips").append(chip);
    });
  }

  $("sentimentTag").textContent = r.sentiment?.label || "neutral";
  const history = r.sentiment_history || [];
  if (history.length) {
    const points = history.map((v, i) => {
      const x = history.length === 1 ? 80 : (i * 160) / (history.length - 1);
      const y = 20 - Math.max(-1, Math.min(1, v)) * 14;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    $("sparkLine").setAttribute("points", points);
    $("sparkLine").setAttribute("stroke", history[history.length - 1] < 0 ? "#b91c1c" : "#15803d");
  }

  $("sources").innerHTML = "";
  if (r.sources?.length) {
    r.sources.forEach((src) => {
      const box = document.createElement("div");
      box.className = "source";
      const title = document.createElement("strong");
      title.textContent = `${src.source}  ·  ${src.score}`;
      const body = document.createElement("span");
      body.textContent = src.text;
      box.append(title, body);
      $("sources").append(box);
    });
  } else {
    $("sources").innerHTML = '<p class="muted small">No lookups yet — ask about pricing, languages or security.</p>';
  }

  if (r.appointment) showAppointment(r.appointment);
  const options = r.suggested_slots || [];
  $("slotOptions").innerHTML = "";
  options.forEach((slot, i) => {
    const btn = document.createElement("button");
    btn.className = "slot" + (selectedSlot?.date === slot.date && selectedSlot?.time === slot.time ? " selected" : "");
    btn.textContent = `${slot.date} · ${slot.time}`;
    btn.onclick = () => {
      selectedSlot = slot;
      [...$("slotOptions").children].forEach((c) => c.classList.remove("selected"));
      btn.classList.add("selected");
    };
    $("slotOptions").append(btn);
    if (i === 0 && !selectedSlot) selectedSlot = slot;
  });
  $("bookBtn").disabled = !options.length;
}

function showAppointment(appt) {
  $("appointment").textContent = `Confirmed: ${appt.date} at ${appt.time} · ${appt.purpose || "Product demo"} · CRM #${appt.id}`;
  $("appointment").className = "appointment confirmed";
}

async function send(text, lang) {
  if (!sid) await startCall(lang || $("langSelect").value);
  if (!text?.trim()) return;
  addBubble("user", text);
  $("textInput").value = "";
  const typing = addBubble("agent", "thinking", "typing");
  const r = await api("/api/message", "POST", { session_id: sid, text, lang: lang || $("langSelect").value });
  typing.remove();
  if (!r.ok) {
    addBubble("agent", r.error || "Something went wrong.");
    return r;
  }
  addBubble("agent", r.message);
  updatePanels(r);
  speak(r.message, r.language);
  return r;
}

async function book() {
  if (!sid) return;
  const r = await api("/api/book", "POST", {
    session_id: sid, date: selectedSlot?.date || "", time: selectedSlot?.time || ""
  });
  if (!r.ok) {
    addBubble("agent", r.error || "That slot is unavailable.");
    return;
  }
  addBubble("agent", r.message);
  showAppointment(r.appointment);
  speak(r.message, "en-IN");
}

async function endCall() {
  if (!sid) return;
  const r = await api("/api/end", "POST", { session_id: sid });
  if (!r.ok) return;
  $("summaryCard").hidden = false;
  $("summaryText").textContent = r.summary;
  $("stageBadge").textContent = "CLOSED";
  $("factsGrid").innerHTML = "";
  Object.entries(r.facts).forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = "fact";
    const label = document.createElement("span");
    label.textContent = key;
    const val = document.createElement("b");
    val.textContent = value;
    item.append(label, val);
    $("factsGrid").append(item);
  });
  $("insights").innerHTML = "";
  r.insights.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    $("insights").append(li);
  });
  $("summaryCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function runDemo() {
  const script = [
    ["Hello, I'm Rabia from Shree Clinic. We need an AI receptionist for incoming calls.", "en-IN"],
    ["Our budget is around 2 lakhs a year, and we want to go live in 2 months.", "en-IN"],
    ["I'm the founder, so I take the final decision.", "en-IN"],
    ["Does it support Hindi, and can it connect to our CRM?", "en-IN"],
    ["Great. Let's book tomorrow at 10 AM.", "en-IN"],
    ["Yes, please confirm.", "en-IN"],
  ];
  demoRunning = true;
  ["demoBtn", "micBtn", "sendBtn", "endBtn", "bookBtn"].forEach((id) => ($(id).disabled = true));
  await startCall("en-IN");
  for (const [line, lang] of script) {
    if (!demoRunning) break;
    $("langSelect").value = lang;
    await sleep(350);
    await send(line, lang);
    await sleep(800);
  }
  if (demoRunning) await endCall();
  demoRunning = false;
  ["demoBtn", "micBtn", "sendBtn", "endBtn"].forEach((id) => ($(id).disabled = false));
  $("bookBtn").disabled = false;
}

/* ---------------------------- voice input ---------------------------- */
function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const rec = new SR();
  rec.continuous = false;
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.onresult = (event) => {
    const text = event.results[0][0].transcript;
    if (text.trim()) send(text, rec.lang);
  };
  rec.onerror = (event) => {
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      stopVoice();
      addBubble("agent", "Microphone access was blocked. You can type your reply instead.");
    }
  };
  rec.onend = () => {
    if (listening) {
      try { rec.start(); } catch (_) { /* already starting */ }
    } else {
      setMicButton();
    }
  };
  return rec;
}

function setMicButton() {
  $("micBtn").classList.toggle("listening", listening);
  $("micLabel").textContent = listening ? "Stop listening" : "Start voice";
}

function startVoice() {
  if (!recognition) recognition = initRecognition();
  if (!recognition) {
    addBubble("agent", "Voice input is not supported here. Use Chrome or Edge, or type your reply.");
    return;
  }
  listening = true;
  recognition.lang = $("langSelect").value;
  setMicButton();
  try { recognition.start(); } catch (_) { /* already running */ }
}

function stopVoice() {
  listening = false;
  if (recognition) {
    try { recognition.stop(); } catch (_) { /* not running */ }
  }
  setMicButton();
}

/* ---------------------------- wiring ---------------------------- */
$("sendBtn").onclick = () => send($("textInput").value);
$("textInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") send($("textInput").value);
});
$("micBtn").onclick = () => (listening ? stopVoice() : startVoice());
$("demoBtn").onclick = runDemo;
$("endBtn").onclick = endCall;
$("bookBtn").onclick = book;
$("resetBtn").onclick = async () => {
  stopVoice();
  await api("/api/reset", "POST", {});
  sid = null;
  $("transcript").innerHTML = "";
  resetPanels();
  addBubble("agent", "Demo data cleared. Starting a fresh call…");
  await startCall($("langSelect").value);
};
$("copyBtn").onclick = async () => {
  const text = [$("summaryText").textContent, "", ...[...$("insights").children].map((li) => "• " + li.textContent)].join("\n");
  try {
    await navigator.clipboard.writeText(text);
    $("copyBtn").textContent = "Copied ✓";
    setTimeout(() => ($("copyBtn").textContent = "Copy"), 1600);
  } catch (_) {
    $("copyBtn").textContent = "Select text to copy";
  }
};

if (!("SpeechRecognition" in window) && !("webkitSpeechRecognition" in window)) {
  document.querySelector(".hint").textContent =
    "Voice input is unavailable in this browser — typing works everywhere. Try Chrome or Edge for microphone input.";
}

startCall();
