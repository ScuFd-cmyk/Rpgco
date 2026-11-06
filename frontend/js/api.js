// Thin HTTP client. The browser never decides outcomes; it asks the server.
const Api = (() => {
  const KEY = "marches.token";
  let token = null;
  try { token = localStorage.getItem(KEY); } catch { /* storage unavailable */ }

  function setToken(t) {
    token = t;
    try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch { /* ignore */ }
  }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      let msg = data.detail;
      if (Array.isArray(msg)) msg = msg.map(d => `${d.loc?.at(-1)}: ${d.msg}`).join("; ");
      const err = new Error(msg || `Request failed (${res.status})`);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  return {
    hasToken: () => !!token, setToken,
    get: p => request("GET", p), post: (p, b) => request("POST", p, b), del: p => request("DELETE", p),
  };
})();
