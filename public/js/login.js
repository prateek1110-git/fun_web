(function () {
  const { api, setSession } = window.FunApi;
  const form = document.getElementById("login-form");
  const select = document.getElementById("name");
  const tease = document.getElementById("tease");
  const error = document.getElementById("error");
  const button = document.getElementById("go");

  const TEASES = {
    Prateek: "Prateek! Only you could believe she'd reply 'sure, 5 mins' and mean it.",
    Ritika: "Ritika! The only person Nishita might actually close Excel for.",
    Yuvraj: "Yuvraj! Brave. She'll check her calendar and say 'let me get back to you'.",
    Nishita: "Oh, look who finally logged off... err, in. Time to block your own calendar, workaholic. 😏",
  };

  const SYMBOLS = ["Σ", "π", "∫", "%", "μ", "σ", "∞", "📊", "☕", "📈", "🧮", "💤"];
  const floaters = document.getElementById("floaters");
  for (let i = 0; i < 26; i++) {
    const item = document.createElement("span");
    item.textContent = SYMBOLS[i % SYMBOLS.length];
    item.style.left = Math.random() * 100 + "%";
    item.style.fontSize = 18 + Math.random() * 30 + "px";
    item.style.animationDuration = 12 + Math.random() * 18 + "s";
    item.style.animationDelay = -Math.random() * 20 + "s";
    floaters.appendChild(item);
  }

  select.addEventListener("change", () => {
    tease.textContent = TEASES[select.value] || "";
    error.textContent = "";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!select.value) {
      error.textContent = "Pick a name first. Even Nishita needs to log in.";
      return;
    }
    button.disabled = true;
    try {
      setSession(await api("login", { name: select.value }));
      window.location.href = "calendar.html";
    } catch (e) {
      error.textContent = e.message;
      button.disabled = false;
    }
  });
})();
