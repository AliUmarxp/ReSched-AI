const { useEffect, useMemo, useState } = React;

function apiErrorMessage(result, fallback) {
  const detail = result?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => `${String(item.loc?.at(-1) || "Field").replace(/_/g, " ")}: ${item.msg}`).join(" · ");
  }
  if (detail?.message) return detail.message;
  return fallback;
}

const API = {
  async login(username, password) {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: username, password }),
    });
    if (!response.ok) throw new Error("Invalid login");
    return response.json();
  },
  async signup(payload) {
    const response = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(result, "Registration failed"));
    return result;
  },
  async logout() {
    await fetch("/api/auth/logout", { method: "POST" });
  },
  async me() {
    const response = await fetch("/api/auth/me");
    if (!response.ok) throw new Error("No active session");
    return response.json();
  },
  async getConstraints() {
    const response = await fetch("/api/constraints");
    if (!response.ok) throw new Error("Unable to load constraints");
    return response.json();
  },
  async saveConstraints(constraints) {
    const response = await fetch("/api/constraints", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ constraints }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to save constraints");
    return result;
  },
  async getRegistrationRequests(status = "pending") {
    const response = await fetch(`/api/admin/requests?status_filter=${encodeURIComponent(status)}`);
    if (!response.ok) throw new Error("Unable to load registration requests");
    return response.json();
  },
  async reviewRegistration(userId, decision, adminNote = "") {
    const response = await fetch(`/api/admin/requests/${userId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, admin_note: adminNote || null }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to review request");
    return result;
  },
  async getData() {
    const response = await fetch("/api/data");
    if (!response.ok) throw new Error("Unable to load data");
    return response.json();
  },
  async seed() {
    const response = await fetch("/api/seed", { method: "POST" });
    const result = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(result, "Unable to reset sample data"));
    return result;
  },
  async saveEntity(name, payload) {
    const response = await fetch(`/api/entities/${name}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(result, "Unable to save data"));
    return result;
  },
  async generate() {
    const response = await fetch("/api/generate", { method: "POST" });
    const result = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(result, "Scheduler failed"));
    return result;
  },
  async importSectionWise() {
    const response = await fetch("/api/import/section-wise", { method: "POST" });
    if (!response.ok) throw new Error("Unable to import section-wise data");
    return response.json();
  },
  async importDataset(dataset) {
    const response = await fetch("/api/import/dataset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, replace: true }),
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = result.detail;
      throw new Error(typeof detail === "string" ? detail : detail?.message || "Dataset validation failed");
    }
    return result;
  },
  async getFreeRooms(day, slotId) {
    const response = await fetch(`/api/rooms/free?day=${encodeURIComponent(day)}&slot_id=${encodeURIComponent(slotId)}`);
    if (!response.ok) throw new Error("Unable to fetch free rooms");
    return response.json();
  },
  async getDataPolicy() {
    const response = await fetch("/api/data-policy");
    if (!response.ok) throw new Error("Unable to fetch data policy");
    return response.json();
  },
};

const USER_NAV = [
  ["dashboard", "Dashboard", "layout-dashboard"],
  ["teachers", "Teachers", "user-round-check"],
  ["courses", "Courses", "book-open-check"],
  ["sections", "Sections", "users-round"],
  ["sectionPlan", "Section Plan", "list-checks"],
  ["rooms", "Rooms/Labs", "building-2"],
  ["repeat", "Repeat Students", "refresh-cw"],
  ["constraints", "Constraints", "sliders-horizontal"],
  ["generate", "Generate", "wand-sparkles"],
  ["timetable", "Timetable", "calendar-days"],
  ["reports", "Reports", "chart-no-axes-combined"],
];

const ADMIN_NAV = [
  ["dashboard", "Admin Overview", "layout-dashboard"],
  ["requests", "Access Requests", "user-plus"],
];

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const ACADEMIC_RULES = [
  "A teacher cannot be double-booked.",
  "A room or lab cannot be double-booked.",
  "A section cannot attend two classes at the same time.",
  "Teacher must be eligible and available for the course.",
  "Room capacity must fit section strength.",
  "Theory uses classrooms; labs use lab rooms.",
  "Labs are scheduled as one continuous block.",
  "3-credit theory courses use a 2+1 weekly split.",
  "2-credit theory courses prefer one continuous 2-hour block.",
  "Same section-course keeps the same teacher all week.",
  "Same section-course lectures are spread across different days.",
  "Repeat-student current and repeated courses cannot clash.",
  "Friday prayer buffer and midday break crossing are protected.",
  "Teacher daily and consecutive loads are capped.",
  "Section daily gaps are capped so students do not wait from morning to late day.",
  "Section consecutive load, daily difficulty, and day span are controlled.",
];

function Icon({ name, className = "" }) {
  return <span className={`icon-shell ${className}`} aria-hidden="true"><i data-lucide={name} /></span>;
}

function normalizeId(value) {
  return String(value || "item")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function toCsvText(value) {
  if (!Array.isArray(value)) return "";
  if (value.length && typeof value[0] === "object") {
    return value.map((item) => `${item.course_id}@${item.section_id}`).join(", ");
  }
  return value.join(", ");
}

function parseFieldValue(field, value) {
  if (field.type === "boolean") return Boolean(value);
  if (field.type === "number") return Number(value) || 0;
  if (Array.isArray(value)) return value;
  if (field.type === "tags" || field.type === "slotTags") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (field.type === "coursePairs") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => {
        const [course_id, section_id] = item.split("@").map((part) => part.trim());
        return { course_id, section_id };
      })
      .filter((item) => item.course_id && item.section_id);
  }
  return value;
}

function weeklyPattern(course) {
  if (!course) return "";
  if (course.type === "lab") return "1 continuous 3-hour lab";
  const credits = Number(course.credit_hours || course.weekly_frequency || 3);
  if (credits === 3) return "2-hour block + 1-hour lecture";
  if (credits === 2) return "1 continuous 2-hour block";
  return `${credits || 1} lecture/week`;
}

function displayValue(value) {
  if (Array.isArray(value)) return toCsvText(value);
  return value === undefined || value === null || value === "" ? "—" : value;
}

function formatCell(field, row) {
  const value = row[field.key];
  if (field.type === "boolean") return value ? "Allowed (max 2)" : "Single session";
  if (field.key === "id") return String(value || "—").toUpperCase();
  if (field.key === "type" || field.key === "program") {
    return String(value || "—").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
  return displayValue(value);
}

function App() {
  const [auth, setAuth] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [activePage, setActivePage] = useState("dashboard");
  const [data, setData] = useState(null);
  const [run, setRun] = useState(null);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!auth || auth.role !== "user") return;
    refresh();
  }, [auth]);

  useEffect(() => {
    API.me().then((result) => setAuth(result.user)).catch(() => setAuth(null)).finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    window.lucide?.createIcons();
  });

  async function handleLogin(username, password) {
    const result = await API.login(username, password);
    setAuth(result.user);
  }

  async function handleLogout() {
    try {
      await API.logout();
    } catch {}
    setAuth(null);
    setData(null);
    setRun(null);
    setSelectedEntry(null);
  }

  async function refresh() {
    setBusy(true);
    try {
      const payload = await API.getData();
      setData(payload.dataset);
      setRun(payload.latestRun);
      setSelectedEntry(payload.latestRun?.entries?.[0] || null);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function runScheduler() {
    setBusy(true);
    setNotice("Scheduler is checking constraints...");
    try {
      const payload = await API.generate();
      setRun(payload.run);
      setSelectedEntry(payload.run.entries?.[0] || null);
      setActivePage("timetable");
      setNotice(`Generated ${payload.run.report.scheduled_sessions} sessions with ${payload.run.report.hard_conflicts} hard conflicts.`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function resetSeed() {
    setBusy(true);
    try {
      const payload = await API.seed();
      setData(payload.dataset);
      setRun(null);
      setSelectedEntry(null);
      setNotice("Seed data restored.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function importSectionWise() {
    setBusy(true);
    setNotice("Importing all section-wise DOCX data...");
    try {
      const payload = await API.importSectionWise();
      setData(payload.dataset);
      setRun(payload.latestRun || null);
      setNotice(`Imported SECTION-WISE from ${payload.importPath}`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveEntity(name, payload) {
    setBusy(true);
    try {
      const response = await API.saveEntity(name, payload);
      setData(response.dataset);
      setNotice("Saved.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  function exportDataset() {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "resched-ai-dataset.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function importDataset(file) {
    if (!file) return;
    const text = await file.text();
    const payload = JSON.parse(text);
    const result = await API.importDataset(payload);
    setData(result.dataset);
    setRun(null);
    setSelectedEntry(null);
    setNotice("Dataset imported.");
  }

  const page = auth?.role === "admin" ? (
    activePage === "requests" ? <AdminRequestsPage /> : <AdminDashboard setActivePage={setActivePage} />
  ) : data ? (
    <PageRouter
      activePage={activePage}
      data={data}
      run={run}
      busy={busy}
      selectedEntry={selectedEntry}
      setSelectedEntry={setSelectedEntry}
      saveEntity={saveEntity}
      runScheduler={runScheduler}
      resetSeed={resetSeed}
      importSectionWise={importSectionWise}
      exportDataset={exportDataset}
      importDataset={importDataset}
      auth={auth}
    />
  ) : (
    <div className="panel p-8">Loading ReSched AI...</div>
  );

  if (checkingSession) {
    return <div className="min-h-screen grid place-items-center bg-slate-50 text-sm font-bold text-slate-600">Checking your session...</div>;
  }

  if (!auth) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell lg:flex">
      <aside className="desktop-sidebar lg:sticky lg:top-0 lg:h-screen lg:w-64 bg-slatepanel text-white p-4">
        <div className="flex items-center gap-3 pb-6">
          <div className="grid h-11 w-11 place-items-center rounded-lg bg-teal text-white">
            <Icon name="brain-circuit" />
          </div>
          <div>
            <div className="text-lg font-black">ReSched</div>
            <div className="text-xs text-slate-300">Academic operations</div>
          </div>
        </div>
        <nav className="grid gap-1">
          {(auth?.role === "admin" ? ADMIN_NAV : USER_NAV).map(([id, label, icon]) => (
            <button
              key={id}
              type="button"
              className={`sidebar-link ${activePage === id ? "active" : ""}`}
              onClick={() => setActivePage(id)}
            >
              <Icon name={icon} />
              <span className="text-sm font-bold">{label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 p-3 md:p-6 xl:p-8">
        <TopBar busy={busy} notice={notice} run={run} onGenerate={runScheduler} onLogout={handleLogout} auth={auth} />
        {page}
      </main>

      {auth?.role === "user" ? <ExplanationPanel entry={selectedEntry} /> : null}
    </div>
  );
}

function TopBar({ busy, notice, run, onGenerate, onLogout, auth }) {
  const isAdmin = auth?.role === "admin";
  return (
    <header className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h1 className="text-2xl font-black tracking-normal text-ink md:text-3xl">{isAdmin ? "Platform Administration" : "Scheduling Workspace"}</h1>
        <div className="mt-1 text-sm text-slate-600">{isAdmin ? "Account approvals and platform oversight" : "Your institution's private scheduling workspace"}</div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {!isAdmin && run?.quality && (
          <div className="rounded-lg border border-emerald-200 bg-white px-4 py-2 text-sm font-extrabold text-emerald-700">
            Score {run.quality.overall}/100
          </div>
        )}
        {notice && <div className="max-w-md rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600">{notice}</div>}
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600">
          {auth?.username}
        </div>
        <button className="btn btn-secondary" type="button" onClick={onLogout}>
          <Icon name="log-out" />
          Logout
        </button>
        {!isAdmin ? <button className="btn btn-primary" type="button" onClick={onGenerate} disabled={busy}>
          <Icon name="wand-sparkles" />
          {busy ? "Working..." : "Generate"}
        </button> : null}
      </div>
    </header>
  );
}

function LoginScreen({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [form, setForm] = useState({
    username: "", email: "", password: "", full_name: "", phone: "",
    institution_name: "", department: "", designation: "", signup_reason: "",
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitSignup(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await API.signup(form);
      setMessage(result.message + ". You can sign in after approval.");
      setMode("login");
      setUsername(form.username);
      setPassword("");
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  function updateSignup(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="min-h-screen grid place-items-center p-5 bg-gradient-to-br from-slate-100 via-white to-teal-50">
      <div className={`panel w-full ${mode === "signup" ? "max-w-3xl" : "max-w-md"} p-6 md:p-8`}>
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-lg bg-teal text-white">
            <Icon name="shield-check" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-ink">ReSched AI</h1>
            <p className="text-sm text-slate-600">Your university scheduling workspace</p>
          </div>
        </div>
        <div className="mt-6 grid grid-cols-2 rounded-lg bg-slate-100 p-1" role="tablist" aria-label="Account access">
          {[['login', 'Sign in'], ['signup', 'Request account']].map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={mode === id} className={`rounded-md px-3 py-2 text-sm font-extrabold ${mode === id ? "bg-white text-ink shadow-sm" : "text-slate-500"}`} onClick={() => { setMode(id); setError(""); }}>
              {label}
            </button>
          ))}
        </div>
        {message ? <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm font-semibold text-emerald-800" role="status">{message}</div> : null}
        {mode === "login" ? <form onSubmit={submit} className="mt-5 grid gap-3">
          <label className="grid gap-1 text-sm">
            <span className="font-bold text-slate-700">Username or email</span>
            <input className="field" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="font-bold text-slate-700">Password</span>
            <input className="field" name="password" autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</div> : null}
          <button className="btn btn-primary" type="submit" disabled={busy}>
            <Icon name="log-in" />
            {busy ? "Signing in..." : "Sign In"}
          </button>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            Accounts must be approved by an administrator before first sign-in.
          </div>
        </form> : <form onSubmit={submitSignup} className="mt-5 grid gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["full_name", "Full name", true], ["username", "Username", true],
              ["email", "Work email", true, "email"], ["phone", "Phone", false],
              ["institution_name", "University / institution", true], ["department", "Department", false],
              ["designation", "Designation", false], ["password", "Password", true, "password"],
            ].map(([key, label, required, type]) => {
              const autocomplete = {
                full_name: "name", username: "username", email: "email", phone: "tel",
                institution_name: "organization", department: "organization-title",
                designation: "off", password: "new-password",
              }[key];
              return (
              <label key={key} className="grid gap-1 text-sm">
                <span className="font-bold text-slate-700">{label}{required ? " *" : ""}</span>
                <input className="field" name={key} autoComplete={autocomplete} required={required} type={type || "text"} value={form[key]} onChange={(event) => updateSignup(key, event.target.value)} />
              </label>
              );
            })}
          </div>
          <label className="grid gap-1 text-sm">
            <span className="font-bold text-slate-700">How will you use ReSched AI?</span>
            <textarea className="field min-h-24" maxLength="1200" value={form.signup_reason} onChange={(event) => updateSignup("signup_reason", event.target.value)} />
          </label>
          {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</div> : null}
          <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Submitting..." : "Submit for approval"}</button>
          <p className="text-xs text-slate-500">Use at least 10 password characters. Your data workspace is created only after approval.</p>
        </form>}
      </div>
    </div>
  );
}

function AdminDashboard({ setActivePage }) {
  const [summary, setSummary] = useState({ pending: 0, approved: 0, denied: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all(["pending", "approved", "denied"].map((status) => API.getRegistrationRequests(status)))
      .then(([pending, approved, denied]) => setSummary({ pending: pending.count, approved: approved.count, denied: denied.count }))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="grid gap-5">
      {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700" role="alert">{error}</div> : null}
      <div className="flex justify-end">
        <button type="button" className="btn btn-primary" onClick={() => setActivePage("requests")}><Icon name="clipboard-check" />Review requests{summary.pending ? ` (${summary.pending})` : ""}</button>
      </div>
      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Pending requests", summary.pending, "user-plus", "text-amber-700"],
          ["Approved accounts", summary.approved, "badge-check", "text-emerald-700"],
          ["Denied requests", summary.denied, "user-x", "text-rose-700"],
        ].map(([label, value, icon, color]) => (
          <div key={label} className="panel p-5">
            <div className="flex items-center justify-between"><span className="text-sm font-extrabold text-slate-600">{label}</span><Icon name={icon} className={color} /></div>
            <div className={`mt-3 text-3xl font-black ${color}`}>{value}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

function PageRouter(props) {
  const { activePage, data, run } = props;
  if (activePage === "teachers") {
    return <EntityManager title="Teachers" name="teachers" rows={data.teachers} fields={teacherFields(data)} onSave={props.saveEntity} />;
  }
  if (activePage === "courses") {
    return <EntityManager title="Courses" name="courses" rows={data.courses} fields={courseFields(data)} onSave={props.saveEntity} />;
  }
  if (activePage === "sections") {
    return <EntityManager title="Sections" name="sections" rows={data.sections} fields={sectionFields(data)} onSave={props.saveEntity} />;
  }
  if (activePage === "sectionPlan") {
    return <SectionPlanner data={data} saveEntity={props.saveEntity} />;
  }
  if (activePage === "rooms") {
    return <EntityManager title="Rooms and Labs" name="rooms" rows={data.rooms} fields={roomFields()} onSave={props.saveEntity} />;
  }
  if (activePage === "repeat") {
    return <EntityManager title="Repeat Students" name="repeatStudents" rows={data.repeatStudents} fields={repeatFields(data)} onSave={props.saveEntity} />;
  }
  if (activePage === "constraints") {
    return <ConstraintsPage />;
  }
  if (activePage === "requests" && props.auth?.role === "admin") {
    return <AdminRequestsPage />;
  }
  if (activePage === "generate") {
    return <GeneratePage {...props} />;
  }
  if (activePage === "timetable") {
    return <TimetablePage data={data} run={run} selectedEntry={props.selectedEntry} setSelectedEntry={props.setSelectedEntry} />;
  }
  if (activePage === "reports") {
    return <ReportsPage data={data} run={run} selectedEntry={props.selectedEntry} setSelectedEntry={props.setSelectedEntry} />;
  }
  return <Dashboard {...props} />;
}

function Dashboard({ data, run, runScheduler, busy, setSelectedEntry, selectedEntry }) {
  const report = run?.report;
  const quality = run?.quality;
  const kpis = [
    ["Hard Conflicts", report?.hard_conflicts ?? 0, "shield-check", "text-emerald-700"],
    ["Repeat Clashes Avoided", report?.repeat_student_clashes_avoided ?? 0, "refresh-cw", "text-teal-700"],
    ["Teacher Clashes Avoided", report?.teacher_clashes_avoided ?? 0, "user-round-check", "text-blue-700"],
    ["Overall Quality", quality ? `${quality.overall}/100` : "--", "gauge", "text-amber-700"],
  ];
  return (
    <div className="grid gap-5">
      <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
        {kpis.map(([label, value, icon, color]) => (
          <div key={label} className="panel p-4">
            <div className="flex items-center justify-between">
              <div className="text-xs font-extrabold uppercase text-slate-500">{label}</div>
              <Icon name={icon} className={color} />
            </div>
            <div className={`mt-3 text-3xl font-black ${color}`}>{value}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-5 2xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-black">Latest Schedule</h2>
              <p className="mt-1 text-sm text-slate-600">{run ? `${report.scheduled_sessions}/${report.total_sessions} sessions scheduled` : "Generate a timetable after your data and rules are ready."}</p>
            </div>
            <button className="btn btn-primary" type="button" onClick={runScheduler} disabled={busy}>
              <Icon name="play" />
              Generate Timetable
            </button>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <QualityMetric label="Hard Constraints" value={quality?.hard_constraints ?? 0} />
            <QualityMetric label="Compactness" value={quality?.compactness ?? 0} />
            <QualityMetric label="Early Release" value={quality?.early_release ?? 0} />
            <QualityMetric label="Teacher Balance" value={quality?.teacher_balance ?? 0} />
          </div>
        </div>
        <div className="panel p-5">
          <h2 className="text-lg font-black">Dataset Snapshot</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <MiniStat label="Programs" value={data.programs.length} />
            <MiniStat label="Sections" value={data.sections.length} />
            <MiniStat label="Teachers" value={data.teachers.length} />
            <MiniStat label="Rooms/Labs" value={data.rooms.length} />
            <MiniStat label="Courses" value={data.courses.length} />
            <MiniStat label="Repeat Cases" value={data.repeatStudents.length} />
          </div>
        </div>
      </section>

    </div>
  );
}

function OperationsPanel({ data }) {
  const [day, setDay] = useState("Monday");
  const [slotId, setSlotId] = useState(data.timeSlots[0]?.id || "mon-p1");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function check() {
    setBusy(true);
    setError("");
    try {
      const payload = await API.getFreeRooms(day, slotId);
      setResult(payload);
    } catch (err) {
      setError(err.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-black">Operations Utility</h2>
          <p className="mt-1 text-sm text-slate-600">Find available rooms for on-the-fly adjustments</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="grid gap-1 text-xs font-bold text-slate-600">
            Day
            <select className="field min-w-36" value={day} onChange={(event) => setDay(event.target.value)}>
              {DAYS.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-xs font-bold text-slate-600">
            Slot
            <select className="field min-w-44" value={slotId} onChange={(event) => setSlotId(event.target.value)}>
              {data.timeSlots.map((slot) => (
                <option key={slot.id} value={slot.id}>{slot.id} ({slot.start_time}-{slot.end_time})</option>
              ))}
            </select>
          </label>
          <button type="button" className="btn btn-secondary" onClick={check} disabled={busy}>
            <Icon name="search-check" />
            {busy ? "Checking..." : "Check Free Rooms"}
          </button>
        </div>
      </div>
      {error ? <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div> : null}
      {result ? (
        <div className="mt-4">
          <div className="text-sm font-bold text-slate-700">{result.count} rooms free on {result.day} ({result.slot_id})</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {result.freeRooms.map((room) => (
              <span key={room.id} className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-bold text-slate-700">
                {room.name} · {room.type}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs font-bold uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black text-ink">{value}</div>
    </div>
  );
}

function QualityMetric({ label, value }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-bold text-slate-700">{label}</span>
        <span className="font-black text-ink">{value}</span>
      </div>
      <div className="metric-bar">
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function RuleBookPanel() {
  return (
    <section className="panel p-5">
      <h2 className="text-xl font-black">Academic Rule Book</h2>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {ACADEMIC_RULES.map((rule) => (
          <div key={rule} className="flex gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <Icon name="check-circle-2" className="mt-0.5 shrink-0 text-teal-700" />
            <span>{rule}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function EntityManager({ title, name, rows, fields, onSave }) {
  const [selectedId, setSelectedId] = useState(rows[0]?.id || "");
  const selected = rows.find((row) => row.id === selectedId) || rows[0] || null;
  const [draft, setDraft] = useState(selected || {});
  const [query, setQuery] = useState("");
  const tableFields = fields.filter((field) => !field.hideInTable);
  const visibleRows = rows.filter((row) => !query.trim() || Object.values(row).some((value) => String(value).toLowerCase().includes(query.trim().toLowerCase())));

  useEffect(() => {
    const next = rows.find((row) => row.id === selectedId) || rows[0] || {};
    setSelectedId(next.id || "");
    setDraft(next);
  }, [rows, selectedId]);

  function selectRow(row) {
    setSelectedId(row.id);
    setDraft(row);
  }

  function update(field, value) {
    setDraft((current) => ({
      ...current,
      [field.key]: parseFieldValue(field, value),
    }));
  }

  function addNew() {
    const base = fields.reduce((acc, field) => {
      if (field.type === "number") acc[field.key] = field.default ?? 0;
      else if (field.type === "tags" || field.type === "slotTags" || field.type === "slotMatrix" || field.type === "coursePairs" || field.type === "coursePicker") acc[field.key] = [];
      else acc[field.key] = field.default ?? "";
      return acc;
    }, {});
    base.id = `${name.slice(0, 2)}-${Date.now().toString(36)}`;
    setSelectedId(base.id);
    setDraft(base);
  }

  async function save() {
    const normalized = { ...draft };
    if (!normalized.id) normalized.id = normalizeId(normalized.name || Date.now());
    const exists = rows.some((row) => row.id === normalized.id);
    const nextRows = exists
      ? rows.map((row) => (row.id === normalized.id ? normalized : row))
      : [...rows, normalized];
    await onSave(name, nextRows);
    setSelectedId(normalized.id);
  }

  async function remove() {
    if (!draft.id) return;
    await onSave(
      name,
      rows.filter((row) => row.id !== draft.id)
    );
  }

  return (
    <section className="grid gap-5 2xl:grid-cols-[1.15fr_0.85fr]">
      <div className="panel overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl font-black">{title}</h2>
            <p className="mt-1 text-sm text-slate-600">{rows.length} records</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input className="field table-search" type="search" placeholder={`Search ${title.toLowerCase()}...`} value={query} onChange={(event) => setQuery(event.target.value)} />
            <button type="button" className="btn btn-primary" onClick={addNew}><Icon name="plus" />Add</button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                {tableFields.map((field) => (
                  <th key={field.key} className="px-4 py-3 font-black">
                    {field.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr
                  key={row.id}
                  className={`cursor-pointer border-t border-slate-100 hover:bg-slate-50 ${selectedId === row.id ? "bg-emerald-50" : ""}`}
                  onClick={() => selectRow(row)}
                >
                  {tableFields.map((field) => (
                    <td key={field.key} className="max-w-[260px] truncate px-4 py-3">
                      {formatCell(field, row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel p-5">
        <h3 className="text-lg font-black">Editor</h3>
        <div className="mt-4 grid gap-3">
          {fields.map((field) => (
            <label key={field.key} className="grid gap-1.5 text-sm">
              <span className="font-bold text-slate-700">{field.label}</span>
              {field.type === "boolean" ? (
                <button type="button" role="switch" aria-checked={Boolean(draft[field.key])} className={`toggle-field ${draft[field.key] ? "on" : ""}`} onClick={() => update(field, !draft[field.key])}>
                  <span className="toggle-knob" /><span>{draft[field.key] ? "Allowed" : "Not allowed"}</span>
                </button>
              ) : field.type === "select" ? (
                <select className="field" value={draft[field.key] ?? ""} onChange={(event) => update(field, event.target.value)}>
                  {(field.options || []).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : field.type === "slotMatrix" ? (
                <SlotMatrix
                  slots={field.slots || []}
                  value={draft[field.key] || []}
                  onChange={(next) => update(field, next)}
                />
              ) : field.type === "coursePicker" ? (
                <CoursePicker
                  courses={field.courses || []}
                  value={draft[field.key] || []}
                  onChange={(next) => update(field, next)}
                />
              ) : field.type === "coursePairs" ? (
                <RepeatCoursePicker
                  courses={field.courses || []}
                  sections={field.sections || []}
                  value={draft[field.key] || []}
                  onChange={(next) => update(field, next)}
                />
              ) : field.type === "tags" || field.type === "slotTags" ? (
                <textarea
                  className="field min-h-20"
                  value={toCsvText(draft[field.key])}
                  onChange={(event) => update(field, event.target.value)}
                />
              ) : (
                <input
                  className="field"
                  type={field.type === "number" ? "number" : "text"}
                  value={draft[field.key] ?? ""}
                  onChange={(event) => update(field, event.target.value)}
                />
              )}
              {field.hint && <span className="text-xs text-slate-500">{field.hint}</span>}
            </label>
          ))}
        </div>
        <div className="mt-5 flex flex-col gap-2 sm:flex-row">
          <button type="button" className="btn btn-primary" onClick={save}>
            <Icon name="save" />
            Save
          </button>
          <button type="button" className="btn btn-danger" onClick={remove}>
            <Icon name="trash-2" />
            Delete
          </button>
        </div>
      </div>
    </section>
  );
}

function SlotMatrix({ slots, value, onChange }) {
  const selected = new Set(value || []);
  const days = DAYS;
  const periods = Array.from(new Map(slots.map((slot) => [slot.period_index, slot])).values())
    .sort((a, b) => a.period_index - b.period_index);

  function toggle(slotId) {
    const next = new Set(selected);
    if (next.has(slotId)) next.delete(slotId);
    else next.add(slotId);
    onChange(Array.from(next));
  }

  function setDay(day, enabled) {
    const next = new Set(selected);
    slots.filter((slot) => slot.day === day).forEach((slot) => {
      if (enabled) next.add(slot.id);
      else next.delete(slot.id);
    });
    onChange(Array.from(next));
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap gap-2">
        {days.map((day) => {
          const daySlots = slots.filter((slot) => slot.day === day);
          const allOn = daySlots.every((slot) => selected.has(slot.id));
          return (
            <button key={day} type="button" className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-slate-700" onClick={() => setDay(day, !allOn)}>
              {allOn ? "Clear" : "All"} {day.slice(0, 3)}
            </button>
          );
        })}
      </div>
      <div className="overflow-x-auto">
        <div className="grid min-w-[720px] gap-1" style={{ gridTemplateColumns: `88px repeat(${periods.length}, minmax(72px, 1fr))` }}>
          <div className="text-xs font-black uppercase text-slate-500">Day</div>
          {periods.map((period) => (
            <div key={period.period_index} className="text-center text-[11px] font-black text-slate-500">
              {period.start_time}
            </div>
          ))}
          {days.map((day) => (
            <React.Fragment key={day}>
              <div className="py-2 text-xs font-black text-slate-700">{day}</div>
              {periods.map((period) => {
                const slot = slots.find((item) => item.day === day && item.period_index === period.period_index);
                const checked = slot && selected.has(slot.id);
                return (
                  <button
                    key={`${day}-${period.period_index}`}
                    type="button"
                    className={`h-9 rounded-md border text-xs font-black ${checked ? "border-teal bg-teal text-white" : "border-slate-200 bg-white text-slate-400"}`}
                    onClick={() => slot && toggle(slot.id)}
                    title={slot ? `${slot.day} ${slot.start_time}-${slot.end_time}` : ""}
                  >
                    {checked ? "On" : "Off"}
                  </button>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

function CoursePicker({ courses, value, onChange }) {
  const selected = new Set(value || []);
  function toggle(courseId) {
    const next = new Set(selected);
    if (next.has(courseId)) next.delete(courseId);
    else next.add(courseId);
    onChange(Array.from(next));
  }
  return (
    <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-2">
      <div className="grid gap-2">
        {courses.map((course) => (
          <button
            key={course.id}
            type="button"
            className={`rounded-lg border p-3 text-left ${selected.has(course.id) ? "border-teal bg-emerald-50" : "border-slate-200 bg-white"}`}
            onClick={() => toggle(course.id)}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-black text-ink">{course.name}</div>
                <div className="mt-1 text-xs font-bold text-slate-500">
                  {course.type} · {weeklyPattern(course)}
                </div>
              </div>
              <div className={`grid h-6 w-6 shrink-0 place-items-center rounded-md text-xs font-black ${selected.has(course.id) ? "bg-teal text-white" : "bg-slate-100 text-slate-400"}`}>
                {selected.has(course.id) ? "✓" : "+"}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function RepeatCoursePicker({ courses, sections, value, onChange }) {
  const pairs = Array.isArray(value) ? value : [];
  const [sectionId, setSectionId] = useState(sections[0]?.id || "");
  const courseMap = Object.fromEntries(courses.map((course) => [course.id, course]));
  const section = sections.find((item) => item.id === sectionId) || sections[0] || null;
  const sectionCourseIds = section?.required_courses?.length ? section.required_courses : courses.map((course) => course.id);
  const availableCourses = sectionCourseIds.map((courseId) => courseMap[courseId]).filter(Boolean);
  const [courseId, setCourseId] = useState(availableCourses[0]?.id || "");

  useEffect(() => {
    if (!sectionId && sections[0]?.id) {
      setSectionId(sections[0].id);
    }
  }, [sectionId, sections]);

  useEffect(() => {
    if (availableCourses.length && !availableCourses.some((course) => course.id === courseId)) {
      setCourseId(availableCourses[0].id);
    }
  }, [availableCourses, courseId]);

  function addPair() {
    if (!sectionId || !courseId) return;
    const exists = pairs.some((pair) => pair.section_id === sectionId && pair.course_id === courseId);
    if (exists) return;
    onChange([...pairs, { course_id: courseId, section_id: sectionId }]);
  }

  function removePair(index) {
    onChange(pairs.filter((_, pairIndex) => pairIndex !== index));
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
        <select className="field bg-white" value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
          {sections.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name || item.id}
            </option>
          ))}
        </select>
        <select className="field bg-white" value={courseId} onChange={(event) => setCourseId(event.target.value)}>
          {availableCourses.map((course) => (
            <option key={course.id} value={course.id}>
              {course.name || course.id}
            </option>
          ))}
        </select>
        <button type="button" className="btn btn-primary justify-center" onClick={addPair} disabled={!sectionId || !courseId}>
          <Icon name="plus" />
          Add
        </button>
      </div>
      <div className="mt-3 grid gap-2">
        {pairs.length ? (
          pairs.map((pair, index) => {
            const pairCourse = courseMap[pair.course_id];
            const pairSection = sections.find((item) => item.id === pair.section_id);
            return (
              <div key={`${pair.section_id}-${pair.course_id}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-black text-ink">{pairCourse?.name || pair.course_id}</div>
                  <div className="mt-0.5 text-xs font-bold text-slate-500">{pairSection?.name || pair.section_id}</div>
                </div>
                <button type="button" className="icon-button shrink-0" onClick={() => removePair(index)} title="Remove">
                  <Icon name="trash-2" />
                </button>
              </div>
            );
          })
        ) : (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white px-3 py-3 text-sm font-bold text-slate-500">No repeated courses selected</div>
        )}
      </div>
    </div>
  );
}

function SectionPlanner({ data, saveEntity }) {
  const [sectionId, setSectionId] = useState(data.sections[0]?.id || "");
  const section = data.sections.find((item) => item.id === sectionId) || data.sections[0];
  const courseMap = Object.fromEntries(data.courses.map((course) => [course.id, course]));
  const selectedCourses = section?.required_courses || [];

  async function updateCourses(nextCourses) {
    const nextSections = data.sections.map((item) =>
      item.id === section.id ? { ...item, required_courses: nextCourses } : item
    );
    await saveEntity("sections", nextSections);
  }

  if (!section) return <EmptyState title="No sections" action="Add sections first." />;

  return (
    <section className="grid gap-5 2xl:grid-cols-[0.75fr_1.25fr]">
      <div className="panel p-5">
        <h2 className="text-xl font-black">Section Subject Plan</h2>
        <p className="mt-1 text-sm text-slate-600">Select a section and assign this semester's subjects.</p>
        <label className="mt-4 grid gap-1 text-sm">
          <span className="font-bold text-slate-700">Section</span>
          <select className="field" value={section.id} onChange={(event) => setSectionId(event.target.value)}>
            {data.sections.map((item) => (
              <option key={item.id} value={item.id}>{item.name} · Semester {item.semester}</option>
            ))}
          </select>
        </label>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <MiniStat label="Subjects" value={selectedCourses.length} />
          <MiniStat label="Weekly Units" value={selectedCourses.reduce((sum, id) => {
            const course = courseMap[id];
            if (!course) return sum;
            return sum + (course.type === "lab" ? 3 : Number(course.credit_hours || course.weekly_frequency || 3));
          }, 0)} />
        </div>
      </div>

      <div className="panel p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-black">{section.name} Subjects</h3>
            <p className="mt-1 text-sm text-slate-600">Theory courses auto-expand by credit hours; labs stay one continuous block.</p>
          </div>
        </div>
        <div className="mt-4">
          <CoursePicker courses={data.courses} value={selectedCourses} onChange={updateCourses} />
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 font-black">Course</th>
                <th className="px-3 py-2 font-black">Type</th>
                <th className="px-3 py-2 font-black">Weekly Rule</th>
                <th className="px-3 py-2 font-black">Teachers</th>
              </tr>
            </thead>
            <tbody>
              {selectedCourses.map((courseId) => {
                const course = courseMap[courseId];
                if (!course) return null;
                return (
                  <tr key={courseId} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-bold">{course.name}</td>
                    <td className="px-3 py-2">{course.type}</td>
                    <td className="px-3 py-2">{weeklyPattern(course)}</td>
                    <td className="px-3 py-2">{toCsvText(course.allowed_teachers)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function teacherFields(data) {
  return [
    { key: "id", label: "ID" },
    { key: "name", label: "Name" },
    { key: "expertise_courses", label: "Expertise", type: "tags", hint: "Course IDs separated by commas" },
    { key: "availability_slots", label: "Availability Matrix", type: "slotMatrix", slots: data.timeSlots, hideInTable: true },
    { key: "max_lectures_per_day", label: "Max/day", type: "number", default: 3 },
  ];
}

function courseFields(data) {
  return [
    { key: "id", label: "ID" },
    { key: "name", label: "Course" },
    { key: "type", label: "Type", type: "select", options: ["theory", "lab"], default: "theory" },
    { key: "duration", label: "Duration", type: "number", default: 1 },
    { key: "credit_hours", label: "Credit Hours", type: "number", default: 3 },
    { key: "contact_hours", label: "Contact Hours", type: "number", default: 3 },
    { key: "weekly_frequency", label: "Lectures/Week", type: "number", default: 3 },
    { key: "difficulty_level", label: "Difficulty", type: "number", default: 3 },
    { key: "allowed_teachers", label: "Allowed Teachers", type: "tags", hint: "Teacher IDs separated by commas", hideInTable: true },
  ];
}

function sectionFields(data) {
  return [
    { key: "id", label: "ID" },
    { key: "program", label: "Program", type: "select", options: data.programs.map((item) => item.name) },
    { key: "degree", label: "Degree" },
    { key: "semester", label: "Semester", type: "number", default: 1 },
    { key: "cohort", label: "Cohort" },
    { key: "name", label: "Section" },
    { key: "strength", label: "Strength", type: "number", default: 35 },
    { key: "required_courses", label: "Required Courses", type: "coursePicker", courses: data.courses, hideInTable: true },
  ];
}

function roomFields() {
  return [
    { key: "id", label: "ID" },
    { key: "name", label: "Room/Lab" },
    { key: "type", label: "Type", type: "select", options: ["classroom", "lab"], default: "classroom" },
    { key: "capacity", label: "Capacity", type: "number", default: 40 },
    { key: "allow_parallel_sessions", label: "Shared at Same Time", type: "boolean", default: false, hint: "Opt in to allow a maximum of two simultaneous sessions in this room. Teacher and section collision rules still apply." },
  ];
}

function repeatFields(data) {
  return [
    { key: "id", label: "ID" },
    { key: "name", label: "Student" },
    { key: "current_section", label: "Current Section", type: "select", options: data.sections.map((item) => item.id) },
    { key: "repeated_courses", label: "Repeated Courses", type: "coursePairs", courses: data.courses, sections: data.sections },
  ];
}

function ConstraintsPage() {
  const [constraints, setConstraints] = useState([]);
  const [busy, setBusy] = useState(true);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    API.getConstraints().then((result) => setConstraints(result.constraints)).catch((error) => setNotice(error.message)).finally(() => setBusy(false));
  }, []);

  function updateConstraint(key, changes) {
    setConstraints((rows) => rows.map((row) => row.key === key ? { ...row, ...changes } : row));
  }

  async function save() {
    setBusy(true);
    setNotice("");
    try {
      const result = await API.saveConstraints(constraints.map((row) => ({
        constraint_key: row.key,
        enabled: row.enabled,
        mode: row.enabled ? row.mode : "off",
        weight: Number(row.weight || 0),
        parameters: row.parameters || {},
      })));
      setConstraints(result.constraints);
      setNotice("Constraint policy saved. Generate a new timetable to apply it.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  const groups = constraints.reduce((result, item) => {
    (result[item.category] ||= []).push(item);
    return result;
  }, {});

  return (
    <div className="grid gap-5">
      <section className="panel p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-xl font-black">Scheduling Constraints</h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">Apply or ignore university policy rules and tune quality priorities. Collision rules are locked because disabling them would create invalid timetables.</p>
          </div>
          <button className="btn btn-primary" type="button" onClick={save} disabled={busy}>{busy ? "Saving..." : "Save policy"}</button>
        </div>
        {notice ? <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm" role="status">{notice}</div> : null}
      </section>
      {Object.entries(groups).map(([category, rows]) => (
        <section key={category} className="panel overflow-hidden">
          <div className="border-b border-slate-200 px-5 py-4"><h3 className="font-black">{category}</h3></div>
          <div className="divide-y divide-slate-100">
            {rows.map((row) => (
              <div key={row.key} className="grid gap-3 p-5 md:grid-cols-[1fr_auto] md:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-black text-ink">{row.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-black ${row.locked ? "bg-slate-100 text-slate-600" : row.mode === "hard" ? "bg-rose-50 text-rose-700" : "bg-blue-50 text-blue-700"}`}>{row.locked ? "Required" : row.mode === "hard" ? "Hard rule" : "Quality rule"}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{row.description}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  {row.mode === "soft" ? <label className="flex items-center gap-2 text-sm font-bold"><span>Weight</span><input className="field w-24" type="number" min="0" max="10" step="0.1" value={row.weight} onChange={(event) => updateConstraint(row.key, { weight: event.target.value })} /></label> : null}
                  <label className="flex items-center gap-2 text-sm font-bold">
                    <input type="checkbox" checked={row.enabled} disabled={row.locked} onChange={(event) => updateConstraint(row.key, { enabled: event.target.checked, mode: event.target.checked ? row.default_mode : "off" })} />
                    {row.enabled ? "Applied" : "Ignored"}
                  </label>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function AdminRequestsPage() {
  const [filter, setFilter] = useState("pending");
  const [requests, setRequests] = useState([]);
  const [busy, setBusy] = useState(true);
  const [notice, setNotice] = useState("");

  async function load(nextFilter = filter) {
    setBusy(true);
    try {
      const result = await API.getRegistrationRequests(nextFilter);
      setRequests(result.requests);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(filter); }, [filter]);

  async function review(id, decision) {
    setBusy(true);
    try {
      await API.reviewRegistration(id, decision);
      setNotice(`Account ${decision}.`);
      await load(filter);
    } catch (error) {
      setNotice(error.message);
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5">
      <section className="panel p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div><h2 className="text-xl font-black">Access Requests</h2><p className="mt-1 text-sm text-slate-600">Review organizations before their private workspace is activated.</p></div>
          <select className="field max-w-48" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="pending">Pending</option><option value="approved">Approved</option><option value="denied">Denied</option></select>
        </div>
        {notice ? <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm" role="status">{notice}</div> : null}
      </section>
      <section className="grid gap-3">
        {!busy && !requests.length ? <EmptyState title="No requests" action={`There are no ${filter} registration requests.`} /> : requests.map((request) => (
          <article key={request.id} className="panel p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-lg font-black">{request.full_name}</div>
                <div className="mt-1 text-sm font-bold text-teal-700">{request.institution_name}</div>
                <div className="mt-2 text-sm text-slate-600">{request.email} · @{request.username}</div>
                <div className="mt-1 text-sm text-slate-600">{[request.designation, request.department, request.phone].filter(Boolean).join(" · ")}</div>
                {request.signup_reason ? <p className="mt-3 max-w-3xl rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{request.signup_reason}</p> : null}
              </div>
              {request.status === "pending" ? <div className="flex gap-2"><button className="btn btn-danger" disabled={busy} onClick={() => review(request.id, "denied")}>Deny</button><button className="btn btn-primary" disabled={busy} onClick={() => review(request.id, "approved")}>Approve</button></div> : <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-black capitalize">{request.status}</span>}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}

function GeneratePage({ data, run, busy, runScheduler, resetSeed, importSectionWise, exportDataset, importDataset, auth }) {
  return (
    <div className="grid gap-5">
      <section className="panel p-5">
        <h2 className="text-xl font-black">Generate Timetable</h2>
        <div className="mt-5 grid gap-3">
          <button className="btn btn-primary" type="button" onClick={runScheduler} disabled={busy}>
            <Icon name="wand-sparkles" />
            Generate Schedule
          </button>
          <a className="btn btn-secondary" href="/api/export/timetable.csv">
            <Icon name="download" />
            Export CSV
          </a>
          <a className="btn btn-secondary" href="/api/export/timetable.pdf">
            <Icon name="file-text" />
            Export PDF
          </a>
          <a className="btn btn-secondary" href="/api/export/section-pdfs.zip">
            <Icon name="file-archive" />
            Section PDFs ZIP
          </a>
          {auth?.is_demo ? <button className="btn btn-secondary" type="button" onClick={importSectionWise} disabled={busy}>
            <Icon name="database-zap" />
            Import SECTION-WISE
          </button> : null}
          <button className="btn btn-secondary" type="button" onClick={exportDataset}>
            <Icon name="database-backup" />
            Export Dataset
          </button>
          <label className="btn btn-secondary cursor-pointer">
            <Icon name="upload" />
            Import Dataset
            <input type="file" accept="application/json" className="hidden" onChange={(event) => importDataset(event.target.files[0])} />
          </label>
          {auth?.is_demo ? <button className="btn btn-danger" type="button" onClick={resetSeed}>
            <Icon name="rotate-ccw" />
            Restore Demo Data
          </button> : null}
        </div>
      </section>

      {run && (
        <section className="panel p-5 2xl:col-span-2">
          <h2 className="text-xl font-black">Latest Run</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <MiniStat label="Sessions" value={`${run.report.scheduled_sessions}/${run.report.total_sessions}`} />
            <MiniStat label="Hard Conflicts" value={run.report.hard_conflicts} />
            <MiniStat label="Quality" value={`${run.quality.overall}/100`} />
            <MiniStat label="Repeat Cases" value={run.report.repeat_student_cases_protected} />
          </div>
        </section>
      )}
    </div>
  );
}

function TimetablePage({ data, run, selectedEntry, setSelectedEntry }) {
  const [view, setView] = useState("section");
  const groups = run?.views?.[view] || {};
  const groupNames = Object.keys(groups);
  const [group, setGroup] = useState(groupNames[0] || "");

  useEffect(() => {
    setGroup(Object.keys(run?.views?.[view] || {})[0] || "");
  }, [view, run]);

  if (!run) {
    return <EmptyState title="No timetable yet" action="Generate from the top-right button." />;
  }

  const entries = groups[group] || [];
  return (
    <section className="panel p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-xl font-black">Timetable View</h2>
          <p className="mt-1 text-sm text-slate-600">Section-wise, teacher-wise, room-wise, and lab-wise schedules</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Segmented value={view} onChange={setView} options={["section", "teacher", "room", "lab"]} />
          <select className="field min-w-48" value={group} onChange={(event) => setGroup(event.target.value)}>
            {groupNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-5 overflow-x-auto">
        <TimetableGrid data={data} entries={entries} selectedEntry={selectedEntry} setSelectedEntry={setSelectedEntry} />
      </div>
    </section>
  );
}

function Segmented({ value, onChange, options }) {
  return (
    <div className="flex rounded-lg border border-slate-200 bg-white p-1">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          className={`rounded-md px-3 py-2 text-sm font-extrabold capitalize ${value === option ? "bg-teal text-white" : "text-slate-600"}`}
          onClick={() => onChange(option)}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function TimetableGrid({ data, entries, selectedEntry, setSelectedEntry }) {
  const periods = useMemo(() => {
    const byIndex = new Map();
    data.timeSlots.forEach((slot) => {
      if (!byIndex.has(slot.period_index)) byIndex.set(slot.period_index, slot);
    });
    return Array.from(byIndex.values()).sort((a, b) => a.period_index - b.period_index);
  }, [data]);
  const columns = useMemo(() => {
    const items = [];
    periods.forEach((period) => {
      items.push({ type: "slot", period });
      if (period.period_index === 4) {
        items.push({ type: "break", id: "midday-break" });
      }
    });
    return items;
  }, [periods]);

  function entriesStartingAt(day, period) {
    return entries.filter(
      (entry) =>
        entry.day === day &&
        Number(entry.start_index) === Number(period.period_index)
    );
  }

  function isCoveredByEarlierEntry(day, period) {
    return entries.some(
      (entry) =>
        entry.day === day &&
        Number(entry.start_index) < Number(period.period_index) &&
        Number(entry.end_index) >= Number(period.period_index)
    );
  }

  const dayColumnWidth = 112;
  const slotColumnWidth = 112;
  const breakColumnWidth = 64;
  const gridMinWidth = dayColumnWidth + columns.reduce((total, column) => total + (column.type === "break" ? breakColumnWidth : slotColumnWidth), 0);

  return (
    <div
      className="timetable-grid"
      style={{
        gridTemplateColumns: `${dayColumnWidth}px ${columns.map((column) => (column.type === "break" ? `${breakColumnWidth}px` : `minmax(${slotColumnWidth}px, 1fr)`)).join(" ")}`,
        minWidth: `${gridMinWidth}px`,
      }}
    >
      <div className="grid-head">Day / Time</div>
      {columns.map((column) => (
        column.type === "break" ? (
          <div key={column.id} className="grid-head grid-break-head">Break<br />12:50<br />13:20</div>
        ) : (
          <div key={column.period.period_index} className="grid-head">
            {column.period.start_time}
            <br />
            {column.period.end_time}
          </div>
        )
      ))}
      {DAYS.map((day) => (
        <React.Fragment key={day}>
          <div className="grid-time">{day}</div>
          {columns.map((column) => {
            if (column.type === "break") {
              return <div key={`${day}-break`} className="grid-break-cell">Break</div>;
            }
            const period = column.period;
            if (isCoveredByEarlierEntry(day, period)) return null;
            const cellEntries = entriesStartingAt(day, period);
            const span = Math.max(1, ...cellEntries.map((entry) => Number(entry.end_index) - Number(entry.start_index) + 1));
            return (
              <div key={`${day}-${period.period_index}`} className="grid-cell" style={{ gridColumn: cellEntries.length ? `span ${span}` : undefined }}>
                {cellEntries.length ? (
                  cellEntries.map((entry) => (
                    <button
                      key={entry.id}
                      type="button"
                      className={`slot-chip ${entry.course_type === "lab" ? "lab" : ""} ${selectedEntry?.id === entry.id ? "active" : ""}`}
                      onClick={() => setSelectedEntry(entry)}
                    >
                      <div className="text-xs font-black uppercase">{entry.section_name}</div>
                      <div className="mt-1 text-sm font-black leading-tight">{entry.course_name}</div>
                      <div className="mt-1 text-xs font-bold opacity-80">{entry.teacher_name}</div>
                      <div className="text-xs opacity-80">{entry.room_name}</div>
                    </button>
                  ))
                ) : (
                  <div className="empty-slot" />
                )}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
}

function ReportsPage({ data, run, selectedEntry, setSelectedEntry }) {
  if (!run) return <EmptyState title="No report yet" action="Generate a timetable first." />;
  const reportItems = [
    ["Hard Conflicts", run.report.hard_conflicts, "shield-check"],
    ["Teacher Clashes Avoided", run.report.teacher_clashes_avoided, "user-round-check"],
    ["Same-Course Teacher Lock", run.report.teacher_consistency_rejections ?? 0, "user-lock"],
    ["Course Day Spread Lock", run.report.course_day_spread_rejections ?? 0, "calendar-range"],
    ["Section Gap Limit Lock", run.report.section_gap_limit_rejections ?? 0, "between-horizontal-start"],
    ["Teacher Daily Balance Warnings", run.report.teacher_daily_overload_warnings ?? 0, "badge-alert"],
    ["Daily Difficulty Warnings", run.report.daily_difficulty_overload_warnings ?? 0, "brain-circuit"],
    ["Teacher Consecutive Warnings", run.report.teacher_consecutive_warnings ?? 0, "timer-reset"],
    ["Section Consecutive Warnings", run.report.section_consecutive_warnings ?? 0, "between-horizontal-start"],
    ["Section Overstretch Warnings", run.report.section_overstretch_warnings ?? 0, "stretch-horizontal"],
    ["Friday Prayer Buffer", run.report.friday_prayer_break_rejections ?? 0, "calendar-clock"],
    ["Break Crossing Blocked", run.report.break_crossing_rejections ?? 0, "pause-circle"],
    ["Room Clashes Avoided", run.report.room_clashes_avoided, "door-open"],
    ["Repeat Student Clashes Avoided", run.report.repeat_student_clashes_avoided, "refresh-cw"],
    ["Lab Allocation Conflicts Avoided", run.report.lab_allocation_conflicts_avoided, "flask-conical"],
    ["Availability Rejections", run.report.availability_rejections, "calendar-x"],
  ];
  return (
    <div className="grid gap-5">
      <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {reportItems.map(([label, value, icon]) => (
          <div key={label} className="panel p-4">
            <div className="flex items-center justify-between">
              <div className="text-sm font-extrabold text-slate-600">{label}</div>
              <Icon name={icon} className="text-teal-700" />
            </div>
            <div className="mt-3 text-3xl font-black text-ink">{value}</div>
          </div>
        ))}
      </section>
      <section className="grid gap-5 2xl:grid-cols-[0.9fr_1.1fr]">
        <div className="panel p-5">
          <h2 className="text-xl font-black">Quality Score</h2>
          <div className="mt-4 grid gap-4">
            {Object.entries(run.quality).map(([key, value]) => (
              <QualityMetric key={key} label={key.replace(/_/g, " ")} value={value} />
            ))}
          </div>
        </div>
        <div className="panel overflow-hidden">
          <div className="border-b border-slate-200 p-5">
            <h2 className="text-xl font-black">Repeat-Student Protection</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-black">Student</th>
                  <th className="px-4 py-3 font-black">Current Section</th>
                  <th className="px-4 py-3 font-black">Repeated Courses</th>
                  <th className="px-4 py-3 font-black">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.repeatStudents.map((student) => (
                  <tr key={student.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-bold">{student.name}</td>
                    <td className="px-4 py-3">{student.current_section}</td>
                    <td className="px-4 py-3">{toCsvText(student.repeated_courses)}</td>
                    <td className="px-4 py-3 font-black text-emerald-700">Protected</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
      <OperationsPanel data={data} />
      <section className="panel p-5">
        <h2 className="text-xl font-black">Constraint Priority and Feasibility</h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase text-slate-500">Priority Framework</div>
            <div className="mt-3 text-sm text-slate-700">
              {(run.report.constraint_priority?.hard_must_have || []).slice(0, 10).join(", ")}
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase text-slate-500">Unscheduled Sessions</div>
            <div className="mt-2 text-2xl font-black text-ink">{run.report.unscheduled_sessions || 0}</div>
            <div className="mt-2 text-sm text-slate-600">If any session is impossible under hard constraints, it is reported with blocker reasons.</div>
          </div>
        </div>
        {(run.report.unscheduled_details || []).length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Session</th>
                  <th className="px-3 py-2">Section</th>
                  <th className="px-3 py-2">Course</th>
                  <th className="px-3 py-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {run.report.unscheduled_details.map((item) => (
                  <tr key={item.session_id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{item.session_id}</td>
                    <td className="px-3 py-2">{item.section_id}</td>
                    <td className="px-3 py-2">{item.course_id}</td>
                    <td className="px-3 py-2">{item.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
      <section className="panel p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-black">Placement Details</h2>
          <a className="btn btn-secondary" href="/api/export/timetable.csv">
            <Icon name="download" />
            CSV
          </a>
          <a className="btn btn-secondary" href="/api/export/timetable.pdf">
            <Icon name="file-text" />
            PDF
          </a>
          <a className="btn btn-secondary" href="/api/export/section-pdfs.zip">
            <Icon name="file-archive" />
            Section ZIP
          </a>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {run.entries.slice(0, 12).map((entry) => (
            <button
              key={entry.id}
              className={`rounded-lg border p-4 text-left ${selectedEntry?.id === entry.id ? "border-teal bg-emerald-50" : "border-slate-200 bg-white"}`}
              type="button"
              onClick={() => setSelectedEntry(entry)}
            >
              <div className="text-sm font-black">{entry.course_name}</div>
              <div className="mt-1 text-xs font-bold text-slate-500">{entry.section_name} · {entry.day} · {entry.start_time}</div>
              <div className="mt-2 text-xs text-slate-600">{entry.explanation[0]}</div>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function SourcePlanPanel({ insights }) {
  if (!insights) return null;
  return (
    <section className="panel p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-xl font-black">Extracted Section-Wise Plan</h2>
          <p className="mt-1 text-sm text-slate-600">
            {insights.documents_count} timetable documents analyzed from {insights.source}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <MiniStat label="Programs" value={insights.programs_found?.length || 0} />
          <MiniStat label="Semesters" value={insights.semesters_found?.length || 0} />
          <MiniStat label="Lab Rooms" value={insights.observed_lab_rooms?.length || 0} />
          <MiniStat label="Real Courses" value={insights.real_courses_used_in_seed?.length || 0} />
        </div>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-black uppercase text-slate-500">Slot Template</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {insights.observed_time_pattern?.map((item) => (
              <span key={item} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-slate-700">
                {item}
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-black uppercase text-slate-500">Seeded From Real Courses</div>
          <div className="mt-2 grid gap-1 text-sm font-semibold text-slate-700">
            {insights.real_courses_used_in_seed?.slice(0, 6).map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
          <div className="text-xs font-black uppercase text-emerald-700">Import Validation</div>
          <div className="mt-2 grid gap-2 text-sm text-emerald-900">
            {insights.ai_ccp_mapping?.slice(0, 3).map((item) => (
              <div key={item} className="flex gap-2">
                <Icon name="check-circle-2" className="mt-0.5 shrink-0" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function AiEvidencePanel({ evidence }) {
  if (!evidence) return null;
  const lists = [
    ["Variable Ordering", evidence.variable_ordering],
    ["Hard Constraints", evidence.hard_constraints],
    ["Soft Constraints", evidence.soft_constraints],
  ];
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black">Scheduling Diagnostics</h2>
          <p className="mt-1 text-sm text-slate-600">
            {evidence.title}. Variables: {evidence.variables}. Domain: {evidence.domain_description}
          </p>
        </div>
        <div className="rounded-lg border border-teal-200 bg-mint px-4 py-3 text-sm font-black text-teal-800">
          Validation Details
        </div>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        {lists.map(([title, items]) => (
          <div key={title} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase text-slate-500">{title}</div>
            <div className="mt-3 grid gap-2">
              {(items || []).slice(0, 7).map((item) => (
                <div key={item} className="flex gap-2 text-sm text-slate-700">
                  <Icon name="dot" className="mt-0.5 shrink-0 text-teal-700" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ExplanationPanel({ entry }) {
  return (
    <aside className="hidden w-72 shrink-0 border-l border-slate-200 bg-white p-5 2xl:block">
      <div className="sticky top-5">
        <div className="flex items-center gap-2">
          <Icon name="sparkles" className="text-teal-700" />
          <h2 className="text-lg font-black">Placement Details</h2>
        </div>
        {entry ? (
          <div className="mt-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-black uppercase text-slate-500">{entry.section_name}</div>
              <div className="mt-1 text-xl font-black leading-tight">{entry.course_name}</div>
              <div className="mt-3 grid gap-2 text-sm text-slate-700">
                <InfoRow label="Teacher" value={entry.teacher_name} />
                <InfoRow label="Room" value={entry.room_name} />
                <InfoRow label="Time" value={`${entry.day}, ${entry.start_time} - ${entry.end_time}`} />
                <InfoRow label="Quality Score" value={entry.soft_score} />
              </div>
            </div>
            <div className="mt-4 grid gap-2">
              {entry.explanation.map((reason) => (
                <div key={reason} className="flex gap-2 rounded-lg border border-slate-200 p-3 text-sm text-slate-700">
                  <Icon name="check-circle-2" className="mt-0.5 shrink-0 text-emerald-700" />
                  <span>{reason}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">Select a class slot.</div>
        )}
      </div>
    </aside>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="font-bold text-slate-500">{label}</span>
      <span className="text-right font-black text-ink">{value}</span>
    </div>
  );
}

function EmptyState({ title, action }) {
  return (
    <section className="panel p-8 text-center">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-lg bg-mint text-teal">
        <Icon name="calendar-clock" />
      </div>
      <h2 className="mt-4 text-xl font-black">{title}</h2>
      <p className="mt-2 text-sm text-slate-600">{action}</p>
    </section>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
