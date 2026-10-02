// Sign-in / create-account / forgot-password form, shared by the account and board pages.
(function () {
  const { sb, esc, friendly } = window.P11;

  function authForm(box, opts) {
    opts = opts || {};
    let mode = opts.mode || "signin";
    const redirect = () => location.origin + location.pathname;
    const titles = { signin: "Sign in", signup: "Create an account", forgot: "Reset your password" };

    function draw(msg, kind) {
      box.innerHTML = `
        <form class="authcard" id="authForm" novalidate>
          <div class="tabs" role="tablist" aria-label="Account options">
            <button type="button" role="tab" data-mode="signin" aria-selected="${mode === "signin"}">Sign in</button>
            <button type="button" role="tab" data-mode="signup" aria-selected="${mode === "signup"}">Create account</button>
          </div>
          <h2>${titles[mode]}</h2>
          ${mode === "signup" ? '<p class="sub">Use the email you want the board to reach you at. You will pick your address after you confirm your email.</p>' : ""}
          <label for="aEmail">Email<input id="aEmail" type="email" autocomplete="email" inputmode="email" required></label>
          ${mode === "forgot" ? "" : `<label for="aPass">Password<input id="aPass" type="password" autocomplete="${mode === "signup" ? "new-password" : "current-password"}" minlength="8" required></label>`}
          <div id="authMsg" class="msg ${kind || ""}" role="status" ${msg ? "" : "hidden"}>${esc(msg || "")}</div>
          <button class="btn" type="submit" id="authGo">${titles[mode] === "Reset your password" ? "Send reset link" : titles[mode]}</button>
          ${mode === "signin" ? '<button class="linkbtn" type="button" data-mode="forgot">Forgot password?</button>' : ""}
          ${mode === "forgot" ? '<button class="linkbtn" type="button" data-mode="signin">Back to sign in</button>' : ""}
        </form>`;
      box.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => { mode = b.dataset.mode; draw(); }));
      box.querySelector("#authForm").addEventListener("submit", submit);
      box.querySelector("#aEmail").focus();
    }
    async function submit(e) {
      e.preventDefault();
      const email = box.querySelector("#aEmail").value.trim();
      const pass = mode === "forgot" ? "" : box.querySelector("#aPass").value;
      const go = box.querySelector("#authGo");
      if (!email) return draw("Enter your email address.", "bad");
      if (mode !== "forgot" && pass.length < 8) return draw("Use a password with at least 8 characters.", "bad");
      go.disabled = true;
      try {
        if (mode === "signin") {
          const { error } = await sb.auth.signInWithPassword({ email, password: pass });
          if (error) throw error;
          if (opts.onSignedIn) opts.onSignedIn();
        } else if (mode === "signup") {
          const { data, error } = await sb.auth.signUp({ email, password: pass, options: { emailRedirectTo: redirect() } });
          if (error) throw error;
          if (data.session) { if (opts.onSignedIn) opts.onSignedIn(); }
          else { mode = "signin"; draw("Check your email for a confirmation link, click it, then come back here and sign in. If you do not see it, look in spam.", "ok"); }
        } else {
          const { error } = await sb.auth.resetPasswordForEmail(email, { redirectTo: redirect() });
          if (error) throw error;
          mode = "signin"; draw("If that email has an account, a reset link is on its way.", "ok");
        }
      } catch (err) {
        draw(friendly(err), "bad");
        box.querySelector("#aEmail").value = email;
      }
    }
    draw();
  }

  // Shown after a password-reset link is opened.
  function recoveryForm(box, onDone) {
    box.innerHTML = `<form class="authcard" id="recForm"><h2>Choose a new password</h2>
      <label for="rPass">New password<input id="rPass" type="password" autocomplete="new-password" minlength="8" required></label>
      <div id="recMsg" class="msg bad" hidden></div><button class="btn" type="submit">Save password</button></form>`;
    box.querySelector("#recForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const p = box.querySelector("#rPass").value, m = box.querySelector("#recMsg");
      if (p.length < 8) { m.hidden = false; m.textContent = "Use a password with at least 8 characters."; return; }
      const { error } = await sb.auth.updateUser({ password: p });
      if (error) { m.hidden = false; m.textContent = friendly(error); return; }
      window.P11.toast("Password updated"); onDone();
    });
  }

  window.P11.authForm = authForm;
  window.P11.recoveryForm = recoveryForm;
})();
