// Shared helpers and Supabase access for every page.
(function () {
  const cfg = window.PINERY;
  const money = (n) => (n < 0 ? "-" : "") + "$" + Math.abs(Number(n) || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const isoDate = (d) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  const parseDate = (s) => { const [y, m, d] = String(s).slice(0, 10).split("-").map(Number); return new Date(y, m - 1, d); };
  const fmtDate = (d) => (d instanceof Date ? d : parseDate(d)).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  const today = () => { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); };
  const daysBetween = (a, b) => Math.round((b - a) / 86400000);
  const cents = (n) => Math.round(Number(n) * 100) / 100;

  // ---- Supabase ----
  const sb = window.supabase && cfg.supabase ? window.supabase.createClient(cfg.supabase.url, cfg.supabase.key) : null;
  async function getUser() {
    if (!sb) return null;
    try { const { data } = await sb.auth.getSession(); return data.session ? data.session.user : null; } catch (e) { return null; }
  }
  async function isBoard() {
    if (!(await getUser())) return false;
    const { data, error } = await sb.rpc("is_board");
    return !error && data === true;
  }
  async function signOut() { if (sb) await sb.auth.signOut(); location.href = "index.html"; }
  const friendly = (e) => {
    const m = (e && e.message) || String(e || "");
    if (/Invalid login/i.test(m)) return "That email and password do not match. Check them or use Forgot password.";
    if (/Email not confirmed/i.test(m)) return "Confirm your email first. Open the message we sent and click the link, then sign in.";
    if (/at least \d+ char/i.test(m)) return "Use a password with at least 8 characters.";
    if (/rate limit/i.test(m)) return "Too many emails were requested. Wait a few minutes and try again.";
    if (/Failed to fetch|NetworkError/i.test(m)) return "Could not reach the database. Check your connection and try again.";
    return m;
  };

  // ---- dues math ----
  // y: a dues_years row; payments/adjustments: rows for one lot (any years).
  function summarize(y, payments, adjustments) {
    const paid = cents(payments.filter((p) => p.year === y.year).reduce((s, p) => s + Number(p.amount), 0));
    const adj = cents(adjustments.filter((a) => a.year === y.year).reduce((s, a) => s + Number(a.amount), 0));
    const billed = cents(Number(y.amount) + adj);
    const balance = cents(billed - paid);
    const due = parseDate(y.due_date);
    const lateAfter = new Date(due); lateAfter.setDate(lateAfter.getDate() + (y.grace_days || 0));
    let status = "unpaid";
    if (balance <= 0) status = "paid";
    else if (today() > due) status = "overdue";
    else if (paid > 0) status = "partial";
    return { year: y.year, billed, paid, balance, due, lateAfter, status, lateFee: Number(y.late_fee) || 0 };
  }
  const statusLabel = { paid: "Paid", partial: "Partial", unpaid: "Unpaid", overdue: "Past due" };

  async function myClaim(user) {
    const { data, error } = await sb.from("claims").select("lot_id,status,created_at").eq("user_id", user.id).maybeSingle();
    return error ? null : data;
  }
  async function loadStatements(lotId) {
    const [y, p, a] = await Promise.all([
      sb.from("dues_years").select("*").order("year", { ascending: false }),
      sb.from("payments").select("*").eq("lot_id", lotId).order("paid_on", { ascending: false }),
      sb.from("adjustments").select("*").eq("lot_id", lotId)
    ]);
    const error = y.error || p.error || a.error;
    const years = y.data || [], payments = (p.data || []).map((r) => ({ ...r, amount: Number(r.amount) })), adjustments = (a.data || []).map((r) => ({ ...r, amount: Number(r.amount) }));
    return { error, years, payments, adjustments, rows: years.map((yr) => summarize(yr, payments, adjustments)) };
  }
  const lotById = (id) => (window.PINERY_LOTS || []).find((l) => l.id === id);

  // ---- theme, nav, toast ----
  const root = document.documentElement;
  try { const t = localStorage.getItem("pinery11-theme"); if (t) root.setAttribute("data-theme", t); } catch (e) {}
  function toggleTheme() {
    const dark = root.getAttribute("data-theme") === "dark" || (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("pinery11-theme", next); } catch (e) {}
  }
  async function renderNav(active) {
    const el = document.getElementById("nav"); if (!el) return;
    const link = (href, text, key, extra = "") => `<a href="${href}"${active === key ? ' aria-current="page"' : ""}${extra}>${text}</a>`;
    const draw = (user, board) => {
      el.innerHTML = link("index.html", "Home", "home") + link("guidelines.html", "Guidelines", "guidelines") + link("account.html", user ? "My dues" : "Sign in", "account") + (board ? link("board.html", "Board", "board") : "") +
        (user ? '<button type="button" id="navOut">Sign out</button>' : "") + '<button type="button" id="themeBtn" aria-label="Switch light and dark theme">Theme</button>';
      document.getElementById("themeBtn").addEventListener("click", toggleTheme);
      const out = document.getElementById("navOut"); if (out) out.addEventListener("click", signOut);
    };
    draw(null, false);
    const user = await getUser();
    if (user) { draw(user, false); draw(user, await isBoard()); }
  }
  let toastTimer;
  function toast(msg) {
    let t = document.getElementById("toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3200);
  }
  async function copyText(text, fallbackEl) {
    try { await navigator.clipboard.writeText(text); toast("Copied"); }
    catch (e) { if (fallbackEl) { fallbackEl.focus(); fallbackEl.select(); } toast("Select the text and copy it"); }
  }
  const brand = () => { const b = document.getElementById("brandName"); if (b) b.textContent = cfg.short; };

  window.P11 = { cfg, sb, money, esc, isoDate, parseDate, fmtDate, today, daysBetween, cents, getUser, isBoard, signOut, myClaim, loadStatements, lotById, friendly, summarize, statusLabel, renderNav, toast, copyText, brand };
})();
