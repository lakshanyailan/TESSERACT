// Login page for Ideanet (demo only: no password is stored or sent anywhere).
// Needs React in scope. Uses an Icon component only for the guest arrow; swap or remove it.
const { useState } = React;

function LField({ id, label, type = "text", ph, msg, auto, value, onChange, bad, children }) {
  return (
    <div className={"field" + (bad ? " bad" : "")}>
      <label htmlFor={"lg-" + id} className="sr">{label}</label>
      <div className="field-in">
        <input id={"lg-" + id} type={type} placeholder={ph} value={value} onChange={onChange} autoComplete={auto} aria-invalid={!!bad} aria-describedby={bad ? "lg-" + id + "-e" : undefined} />
        {children}
      </div>
      {bad && <small id={"lg-" + id + "-e"} role="alert">{msg}</small>}
    </div>
  );
}

function Login({ onEnter, notify }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ fn: "", ln: "", em: "", pw: "", tc: false });
  const [err, setErr] = useState({});
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const signup = mode === "signup";
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }); setErr({ ...err, [k]: false }); };
  const switchMode = (m) => { setMode(m); setErr({}); };
  const submit = (e) => {
    e.preventDefault();
    const x = {};
    if (signup) { x.fn = !f.fn.trim(); x.ln = !f.ln.trim(); x.tc = !f.tc; }
    x.em = !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.em);
    x.pw = f.pw.length < 8;
    setErr(x);
    if (Object.values(x).some(Boolean)) return;
    setBusy(true);
    setTimeout(() => {
      const name = signup ? (f.fn.trim() + " " + f.ln.trim()) : f.em.split("@")[0].replace(/[._-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      onEnter({ name, email: f.em });
    }, 900);
  };
  return (
    <main className="login-page">
      <div className="login-col">
        <header className="login-brand">
          <span className="logo">ideanet</span>
          <p>Where ideas meet innovators.</p>
        </header>

        <h1>{signup ? "Create an account" : "Welcome back"}</h1>
        <form onSubmit={submit} noValidate>
          {signup && (
            <div className="two">
              <LField id="fn" label="First name" ph="First name" msg="Required." auto="given-name" value={f.fn} onChange={set("fn")} bad={err.fn} />
              <LField id="ln" label="Last name" ph="Last name" msg="Required." auto="family-name" value={f.ln} onChange={set("ln")} bad={err.ln} />
            </div>
          )}
          <LField id="em" type="email" label="Email" ph="Email" msg="Enter a valid email address." auto="email" value={f.em} onChange={set("em")} bad={err.em} />
          <LField id="pw" type={show ? "text" : "password"} label="Password" ph="Password" msg="Password must be at least 8 characters." auto={signup ? "new-password" : "current-password"} value={f.pw} onChange={set("pw")} bad={err.pw}>
            <button type="button" className="eye" onClick={() => setShow(!show)} aria-pressed={show} aria-label={show ? "Hide password" : "Show password"}>{show ? "Hide" : "Show"}</button>
          </LField>
          {signup ? (
            <div className={"check" + (err.tc ? " bad" : "")}>
              <label><input type="checkbox" checked={f.tc} onChange={set("tc")} /> I agree to the <button type="button" className="textlink" onClick={() => notify("Terms are a placeholder in this prototype.")}>Terms and Conditions</button></label>
              {err.tc && <small role="alert">Please accept the terms to continue.</small>}
            </div>
          ) : (
            <div className="check split">
              <label><input type="checkbox" /> Remember me</label>
              <button type="button" className="textlink" onClick={() => notify("Password reset is a placeholder for now.")}>Forgot password?</button>
            </div>
          )}
          <button type="submit" className="btn block go" disabled={busy}>{busy ? <><span className="spin" />{signup ? "Creating account" : "Signing in"}</> : signup ? "Create account" : "Log in"}</button>
        </form>

        <div className="or">or</div>
        <div className="soc">
          <button type="button" onClick={() => notify("Google sign-in is not connected in this prototype.")}>Google</button>
          <button type="button" onClick={() => notify("GitHub sign-in is not connected in this prototype.")}>GitHub</button>
        </div>
        <p className="login-switch">
          {signup ? "Already have an account? " : "New to Ideanet? "}
          <button type="button" className="textlink" onClick={() => switchMode(signup ? "login" : "signup")}>{signup ? "Log in" : "Create an account"}</button>
        </p>
        <button type="button" className="guest" onClick={() => onEnter({ name: "Guest", email: "", goExplore: true })}>Just testing an idea? Continue as guest <Icon n="up" size={14} /></button>
      </div>
    </main>
  );
}
