(function () {
  const KEY = "book_nishita_session";

  function getSession() {
    try {
      return JSON.parse(sessionStorage.getItem(KEY));
    } catch (e) {
      return null;
    }
  }

  function setSession(session) {
    sessionStorage.setItem(KEY, JSON.stringify(session));
  }

  function clearSession() {
    sessionStorage.removeItem(KEY);
  }

  async function api(path, body) {
    const session = getSession();
    const headers = { "Content-Type": "application/json" };
    if (session) headers.Authorization = "Bearer " + session.token;
    const response = await fetch("/api/" + path, {
      method: body ? "POST" : "GET",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || "Something went wrong.");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  window.FunApi = { api, getSession, setSession, clearSession };
})();
