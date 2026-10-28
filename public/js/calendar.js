(function () {
  const { api, getSession, clearSession } = window.FunApi;
  const session = getSession();
  if (!session) {
    window.location.replace("index.html");
    return;
  }

  const isOwner = session.role === "owner";
  const FIRST_HOUR = 6;
  const LAST_HOUR = 23;
  const DAYS = 7;

  const BUSY_EVENTS = [
    { title: "Quarterly Reserving Review", icon: "📊" },
    { title: "Staring at Excel (again)", icon: "🧮" },
    { title: "Pivot Table Therapy", icon: "🧪" },
    { title: "Explaining IBNR to Non-Actuaries", icon: "🙄" },
    { title: "Monte Carlo: 10,000 Simulations", icon: "🎲" },
    { title: "Deadline Panic (scheduled)", icon: "⏰" },
    { title: "Mortality Table Meditation", icon: "📉" },
    { title: "Lunch at Desk (sad)", icon: "🥪" },
    { title: "Reply-All Email Marathon", icon: "📧" },
    { title: "Sleep (lol, as if)", icon: "😴" },
  ];
  const ICONS = Object.fromEntries(BUSY_EVENTS.map((e) => [e.title, e.icon]));

  const APPOINTMENTS = [
    { kind: "Chai break", icon: "☕" },
    { kind: "Coffee date", icon: "🥤" },
    { kind: "Lunch", icon: "🍱" },
    { kind: "Dinner", icon: "🍕" },
    { kind: "Walk outside (sunlight!)", icon: "🌳" },
    { kind: "Gossip session", icon: "🗣️" },
    { kind: "Roast Nishita", icon: "🔥" },
    { kind: "Rescue from Excel", icon: "🛟" },
    { kind: "Ice cream emergency", icon: "🍦" },
    { kind: "Movie night", icon: "🎬" },
    { kind: "Gaming session", icon: "🎮" },
    { kind: "Shopping therapy", icon: "🛍️" },
    { kind: "Birthday / celebration", icon: "🎂" },
    { kind: "Venting about work", icon: "😤" },
    { kind: "Just to check you're alive", icon: "💓" },
    { kind: "Gym buddy", icon: "🏋️" },
    { kind: "Book club (we read 1 page)", icon: "📚" },
    { kind: "Midnight snack run", icon: "🌮" },
  ];
  const CUSTOM = { kind: "Custom reason", icon: "✏️", custom: true };
  const APPT_ICONS = Object.fromEntries(APPOINTMENTS.map((a) => [a.kind, a.icon]));

  const TICKER = [
    "Breaking: Nishita spotted away from her laptop. Experts say it was a screensaver.",
    "Nishita's work-life balance: a rounding error.",
    "She doesn't have a 9-to-5. She has a 9-to-9, plus bonus midnight.",
    "Fun fact: Nishita's calendar has more blocks than a blockchain.",
    "Actuaries predict the future. Nishita predicts she'll be 'done in 5 mins'.",
    "Her favourite hobby: 'just one more pivot table'.",
    "Sources confirm: chai is the only thing that can pause a deadline.",
  ];

  const state = { data: null, day: 0 };
  const $ = (id) => document.getElementById(id);

  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (key === "class") node.className = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    });
    children.flat().forEach((child) => node.append(child));
    return node;
  }

  const pad = (n) => String(n).padStart(2, "0");
  const dateKey = (d) => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  const slotKey = (day, hour) => dateKey(day) + "T" + pad(hour);
  const hourLabel = (h) => (h % 12 || 12) + (h % 24 < 12 ? " AM" : " PM");
  const hourRange = (h) => hourLabel(h) + " – " + hourLabel((h + 1) % 24);
  const hourIcon = (h) => (h < 12 ? "🌅" : h < 18 ? "☀️" : "🌙");

  function days() {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    return Array.from({ length: DAYS }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }

  function isPast(day, hour) {
    return new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour + 1).getTime() <= Date.now();
  }

  function slotInfo(day, hour) {
    const key = slotKey(day, hour);
    const { blocks, bookings } = state.data;
    if (blocks[key]) return { key, type: "blocked", block: blocks[key] };
    if (bookings[key]) {
      const mine = bookings[key].by === session.name;
      return { key, type: mine ? "mine" : "taken", booking: bookings[key] };
    }
    if (isPast(day, hour)) return { key, type: "past" };
    return { key, type: "free" };
  }

  function toast(message) {
    const node = $("toast");
    node.textContent = message;
    node.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => node.classList.remove("show"), 4200);
  }

  function confetti() {
    const layer = $("confetti");
    const bits = ["🎉", "✨", "☕", "🎊", "💃", "🍰"];
    for (let i = 0; i < 40; i++) {
      const bit = el("span", {}, bits[i % bits.length]);
      bit.style.left = Math.random() * 100 + "%";
      bit.style.animationDelay = Math.random() * 0.8 + "s";
      layer.append(bit);
      setTimeout(() => bit.remove(), 4000);
    }
  }

  function openModal(...content) {
    const body = $("modal-body");
    body.replaceChildren(...content);
    $("modal").hidden = false;
  }

  const closeModal = () => ($("modal").hidden = true);

  function chips(options, onPick) {
    const wrap = el("div", { class: "chips" });
    options.forEach((option) => {
      const chip = el("button", { type: "button", class: "chip" }, option.icon + " " + (option.title || option.kind));
      chip.addEventListener("click", () => {
        wrap.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        onPick(option);
      });
      wrap.append(chip);
    });
    return wrap;
  }

  async function run(action, successMessage) {
    try {
      await action();
      closeModal();
      if (successMessage) toast(successMessage);
      await refresh();
      return true;
    } catch (e) {
      if (e.status === 401) {
        clearSession();
        window.location.replace("index.html");
      } else {
        toast("⚠️ " + e.message);
        refresh().catch(() => {});
      }
      return false;
    }
  }

  function dayLabel(day) {
    return day.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
  }

  function slotTitle(key) {
    const [date, hour] = key.split("T");
    const [y, m, d] = date.split("-").map(Number);
    return dayLabel(new Date(y, m - 1, d)) + " · " + hourRange(Number(hour));
  }

  function bookDialog(info, day, hour) {
    let picked = null;
    const custom = el("input", { type: "text", maxlength: "60", placeholder: "Your reason for stealing her time…" });
    custom.hidden = true;
    const note = el("textarea", { maxlength: "140", placeholder: "Add a note (e.g. 'Bring snacks, you've forgotten what lunch is')" });
    const confirm = el("button", { class: "btn", disabled: "" }, "Lock it in 🔐");
    const sync = () => (confirm.disabled = !picked || (picked.custom && !custom.value.trim()));
    const choice = chips(APPOINTMENTS.concat(CUSTOM), (option) => {
      picked = option;
      custom.hidden = !option.custom;
      if (option.custom) custom.focus();
      sync();
    });
    custom.addEventListener("input", sync);
    confirm.addEventListener("click", () =>
      run(
        () =>
          api("book", { slot: info.key, kind: picked.custom ? custom.value.trim() : picked.kind, note: note.value }).then(() => confetti()),
        "Booked! Nishita will say she's 'just finishing one thing'. 😏"
      )
    );
    openModal(
      el("h3", {}, "Steal an hour from Nishita"),
      el("p", { class: "muted" }, slotTitle(info.key) + " " + hourIcon(hour)),
      el("p", {}, "What's the plan?"),
      choice,
      custom,
      note,
      el("div", { class: "actions" }, el("button", { class: "btn ghost", onclick: closeModal }, "Cancel"), confirm)
    );
  }

  function blockDialog(info, day, hour) {
    let picked = null;
    const custom = el("input", { type: "text", maxlength: "60", placeholder: "…or type your own excuse" });
    const confirm = el("button", { class: "btn", disabled: "" }, "Block it 🔒");
    const sync = () => (confirm.disabled = !(custom.value.trim() || picked));
    const choice = chips(BUSY_EVENTS, (option) => {
      picked = option;
      custom.value = "";
      sync();
    });
    custom.addEventListener("input", () => {
      picked = null;
      choice.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      sync();
    });
    confirm.addEventListener("click", () => {
      const title = custom.value.trim() || picked.title;
      run(() => api("block", { items: [{ slot: info.key, title }] }), "Blocked. Nobody can touch your time. (Except you, by working.)");
    });
    openModal(
      el("h3", {}, "What's keeping you busy?"),
      el("p", { class: "muted" }, slotTitle(info.key) + " " + hourIcon(hour)),
      choice,
      custom,
      el("div", { class: "actions" }, el("button", { class: "btn ghost", onclick: closeModal }, "Cancel"), confirm)
    );
  }

  function blockedDialog(info) {
    openModal(
      el("h3", {}, (ICONS[info.block.title] || "🔒") + " " + info.block.title),
      el("p", { class: "muted" }, slotTitle(info.key)),
      isOwner
        ? el("p", {}, "Are you sure you want to free this slot? Your inbox will notice.")
        : el("p", {}, "Nishita is 'busy'. Sadly, spreadsheets outrank friends this hour."),
      el(
        "div",
        { class: "actions" },
        el("button", { class: "btn ghost", onclick: closeModal }, isOwner ? "Keep it blocked" : "Fine, I'll respect it"),
        isOwner
          ? el("button", { class: "btn", onclick: () => run(() => api("unblock", { slot: info.key }), "Freed! A rare moment of rest.") }, "Unblock 🕊️")
          : ""
      )
    );
  }

  function onSlotClick(info, day, hour) {
    if (info.type === "past") return;
    if (info.type === "blocked") return blockedDialog(info);
    if (info.type === "taken" || info.type === "mine") {
      return openModal(
        el("h3", {}, (APPT_ICONS[info.booking.kind] || "📌") + " " + info.booking.kind),
        el("p", { class: "muted" }, slotTitle(info.key) + " · by " + info.booking.by),
        info.booking.note ? el("p", {}, "“" + info.booking.note + "”") : "",
        el(
          "div",
          { class: "actions" },
          el("button", { class: "btn ghost", onclick: closeModal }, "Close"),
          isOwner || info.type === "mine"
            ? el("button", { class: "btn", onclick: () => run(() => api("cancel", { slot: info.key }), isOwner ? "Declined. Savage." : "Cancelled.") }, isOwner ? "Decline 😈" : "Cancel mine")
            : ""
        )
      );
    }
    if (isOwner) return blockDialog(info, day, hour);
    return bookDialog(info, day, hour);
  }

  function renderDays() {
    const tabs = $("days");
    tabs.replaceChildren(
      ...days().map((day, index) =>
        el(
          "button",
          {
            class: "day" + (index === state.day ? " active" : ""),
            role: "tab",
            "aria-selected": String(index === state.day),
            onclick: () => {
              state.day = index;
              render();
            },
          },
          el("span", { class: "dow" }, index === 0 ? "Today" : day.toLocaleDateString(undefined, { weekday: "short" })),
          el("span", { class: "dom" }, String(day.getDate()))
        )
      )
    );
  }

  function slotTile(day, hour) {
    const info = slotInfo(day, hour);
    let icon = hourIcon(hour);
    let text = "Free ✨";
    if (info.type === "blocked") [icon, text] = [ICONS[info.block.title] || "🔒", info.block.title];
    if (info.type === "taken") [icon, text] = [APPT_ICONS[info.booking.kind] || "📌", "Taken by " + info.booking.by];
    if (info.type === "mine") [icon, text] = [APPT_ICONS[info.booking.kind] || "📌", "You: " + info.booking.kind];
    if (info.type === "past") text = "Gone ⏳";
    const tile = el(
      "button",
      { class: "slot " + info.type, onclick: () => onSlotClick(info, day, hour), "aria-label": hourRange(hour) + ": " + text },
      el("span", { class: "slot-time" }, hourIcon(hour) + " " + hourRange(hour)),
      el("span", { class: "slot-text" }, (info.type === "free" ? "" : icon + " ") + text)
    );
    if (info.type === "past") tile.disabled = true;
    return tile;
  }

  function renderSlots() {
    const day = days()[state.day];
    const hours = Array.from({ length: LAST_HOUR - FIRST_HOUR + 1 }, (_, i) => FIRST_HOUR + i);
    $("slots").replaceChildren(...hours.map((hour) => slotTile(day, hour)));
  }

  function renderStats() {
    let total = 0;
    let free = 0;
    days().forEach((day) => {
      for (let hour = FIRST_HOUR; hour <= LAST_HOUR; hour++) {
        if (isPast(day, hour)) continue;
        total++;
        if (slotInfo(day, hour).type === "free") free++;
      }
    });
    const busy = total ? Math.round(((total - free) / total) * 100) : 100;
    $("stat-free").textContent = String(free);
    $("stat-busy").textContent = busy + "%";
    $("meter-fill").style.width = busy + "%";
    $("meter-note").textContent =
      busy < 20
        ? "Suspiciously free. Is Nishita feeling okay? Has she been fired from Excel?"
        : busy < 60
        ? "Still some air in the calendar. Strike before the next deadline."
        : busy < 90
        ? "Getting crowded. She's turning into a spreadsheet."
        : "Fully booked. She is now a certified human calculator.";
  }

  function renderList() {
    const entries = Object.entries(state.data.bookings)
      .filter(([, booking]) => isOwner || booking.by === session.name)
      .sort(([a], [b]) => a.localeCompare(b));
    $("list-title").textContent = isOwner ? "Requests from people who want you to rest" : "Your appointments with Nishita";
    $("bookings").replaceChildren(
      ...(entries.length
        ? entries.map(([key, booking]) =>
            el(
              "li",
              {},
              el("span", { class: "li-icon" }, APPT_ICONS[booking.kind] || "📌"),
              el(
                "span",
                { class: "li-text" },
                el("strong", {}, isOwner ? booking.by + ": " + booking.kind : booking.kind),
                el("small", {}, slotTitle(key) + (booking.note ? " — “" + booking.note + "”" : ""))
              ),
              el(
                "button",
                { class: "btn small ghost", onclick: () => run(() => api("cancel", { slot: key }), isOwner ? "Declined. Savage." : "Cancelled.") },
                isOwner ? "Decline" : "Cancel"
              )
            )
          )
        : [el("li", { class: "empty" }, isOwner ? "Nobody yet. Your calendar is safe… for now." : "Nothing yet. Nishita is waiting (reading emails).")])
    );
  }

  function render() {
    renderDays();
    renderSlots();
    renderStats();
    renderList();
  }

  async function refresh() {
    state.data = await api("calendar");
    render();
  }

  function setupHeader() {
    $("who").textContent = session.name;
    $("ticker").textContent = TICKER.concat(TICKER).join("   •   ");
    $("logout").addEventListener("click", () => {
      clearSession();
      window.location.href = "index.html";
    });
    $("modal").addEventListener("click", (event) => {
      if (event.target === $("modal")) closeModal();
    });
    if (isOwner) {
      $("hero-title").textContent = "Hey Nishita, time to hide 🙈";
      $("hero-sub").textContent =
        "Prateek, Ritika and Yuvraj are coming for your time. Block your calendar with important-sounding work before they book you for fun.";
      $("owner-tools").hidden = false;
      $("block-day").addEventListener("click", blockWholeDay);
    } else {
      $("hero-title").textContent = "Hi " + session.name + "! Let's steal an hour 🕵️";
      $("hero-sub").textContent = "Pick a day, find a free slot (good luck), and schedule time with the busiest actuary in town. Don't expect much.";
    }
  }

  function blockWholeDay() {
    const day = days()[state.day];
    const items = [];
    for (let hour = FIRST_HOUR; hour <= LAST_HOUR; hour++) {
      if (slotInfo(day, hour).type === "free") {
        items.push({ slot: slotKey(day, hour), title: BUSY_EVENTS[(hour + items.length) % BUSY_EVENTS.length].title });
      }
    }
    if (!items.length) return toast("Nothing left to block. You're already a legend.");
    run(() => api("block", { items }), "Whole day blocked. Even Sunday should be scared of you.");
  }

  function welcome() {
    const ok = el("button", { class: "btn" }, isOwner ? "Fine, let's hide 🫣" : "Fine, I'll manage 😅");
    ok.addEventListener("click", closeModal);
    openModal(
      el("h3", {}, isOwner ? "🛑 Plot twist, Nishita" : "⏱ Only 15 minutes!"),
      el(
        "p",
        {},
        isOwner
          ? "Your friends are about to book you for fun. Block slots with your most boring work events and they won't be able to schedule anything there."
          : "Nishita can give you only 15 minutes, so don't hope for much. Pick your slot wisely."
      ),
      el("div", { class: "actions" }, ok)
    );
  }

  setupHeader();
  refresh()
    .then(() => {
      welcome();
      setInterval(() => refresh().catch(() => {}), 10000);
    })
    .catch(() => {
      clearSession();
      window.location.replace("index.html");
    });
})();
