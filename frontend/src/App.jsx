import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000/api";

const scoreColor = (s) =>
  s >= 75 ? "text-emerald-400" : s >= 50 ? "text-amber-400" : "text-red-400";
const scoreBg = (s) =>
  s >= 75 ? "bg-emerald-400/10 border-emerald-400/20" : s >= 50 ? "bg-amber-400/10 border-amber-400/20" : "bg-red-400/10 border-red-400/20";
const barColor = (s) =>
  s >= 75 ? "bg-emerald-400" : s >= 50 ? "bg-amber-400" : "bg-red-400";
const severityBorder = (sev) =>
  sev === "high" ? "border-l-red-500" : sev === "medium" ? "border-l-amber-500" : "border-l-emerald-500";
const severityText = (sev) =>
  sev === "high" ? "text-red-400" : sev === "medium" ? "text-amber-400" : "text-emerald-400";
const confidenceBadge = (c) =>
  c === "high" ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/20"
  : c === "medium" ? "bg-amber-400/10 text-amber-400 border-amber-400/20"
  : "bg-red-400/10 text-red-400 border-red-400/20";

function StatCard({ label, value, color }) {
  return (
    <div className="bg-[#13131a] border border-[#2a2a35] rounded-xl p-5">
      <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">{label}</p>
      <p className={`text-3xl font-bold tracking-tight ${color}`}>{value ?? "—"}</p>
    </div>
  );
}

function FlagItem({ flag }) {
  return (
    <div className={`border-l-2 ${severityBorder(flag.severity)} bg-[#13131a] rounded-r-lg px-4 py-3`}>
      <p className={`text-[10px] uppercase tracking-wider mb-1 ${severityText(flag.severity)}`}>{flag.rule}</p>
      <p className="text-xs text-zinc-400 leading-relaxed">{flag.message}</p>
    </div>
  );
}

function ResultPanel({ data }) {
  if (!data) return null;
  const score = data.overall_score ?? 0;
  return (
    <div className="mt-6 border border-[#2a2a35] rounded-xl p-5 bg-[#0d0d0f] animate-fade-in">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className={`text-4xl font-bold tracking-tight ${scoreColor(score)}`}>{score}</p>
          <p className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">overall score</p>
        </div>
        <div className="text-right">
          <span className={`inline-block text-xs px-3 py-1 rounded-full border ${data.passed ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/20" : "bg-red-400/10 text-red-400 border-red-400/20"}`}>
            {data.passed ? "✓ Passed" : "✗ Failed"}
          </span>
          {data.confidence_level && (
            <span className={`inline-block text-xs px-3 py-1 rounded-full border ml-2 ${confidenceBadge(data.confidence_level)}`}>
              {data.confidence_level} confidence
            </span>
          )}
        </div>
      </div>

      <div className="w-full h-1 bg-[#2a2a35] rounded-full mb-5">
        <div className={`h-1 rounded-full transition-all duration-700 ${barColor(score)}`} style={{ width: `${score}%` }} />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="bg-[#13131a] rounded-lg px-4 py-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-600">Rule Score</p>
          <p className="text-xl font-semibold text-violet-400 mt-1">{data.rule_score ?? "—"}</p>
        </div>
        <div className="bg-[#13131a] rounded-lg px-4 py-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-600">AI Score</p>
          <p className="text-xl font-semibold text-teal-400 mt-1">{data.ai_score ?? "—"}</p>
        </div>
      </div>

      {data.flags?.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-3">{data.flags.length} flag(s) detected</p>
          {data.flags.map((f, i) => <FlagItem key={i} flag={f} />)}
        </div>
      ) : (
        <p className="text-xs text-zinc-600 py-2">No flags raised — submission passed all checks.</p>
      )}
    </div>
  );
}

function SubmissionForm({ onSubmitted }) {
  const empty = { name: "", email: "", company: "", title: "", level: "", location: "", years_of_experience: "", base_salary: "", bonus: "", stock_rsu: "", total_compensation: "" };
  const [form, setForm] = useState(empty);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setError(""); setResult(null);
    if (!form.name || !form.email || !form.company || !form.title) {
      setError("Name, email, company and title are required."); return;
    }
    setLoading(true);
    try {
      const payload = {
        ...form,
        years_of_experience: parseInt(form.years_of_experience) || 0,
        base_salary: parseInt(form.base_salary) || 0,
        bonus: parseInt(form.bonus) || 0,
        stock_rsu: parseInt(form.stock_rsu) || 0,
        total_compensation: parseInt(form.total_compensation) || 0,
      };
      const r = await fetch(`${API}/submissions/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await r.json();
      if (!r.ok) { setError(JSON.stringify(data.details || data.error || "Submission failed.")); return; }
      setResult(data);
      onSubmitted();
    } catch {
      setError("Could not reach backend. Make sure Django is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const Field = ({ label, id, type = "text", placeholder }) => (
    <div className="flex flex-col gap-1.5">
      <label className="text-[10px] uppercase tracking-widest text-zinc-600">{label}</label>
      <input
        type={type} placeholder={placeholder} value={form[id]}
        onChange={set(id)}
        className="bg-[#0d0d0f] border border-[#2a2a35] rounded-lg px-3 py-2 text-sm text-zinc-200 font-mono placeholder-zinc-700 focus:outline-none focus:border-violet-500 transition-colors"
      />
    </div>
  );

  return (
    <div className="bg-[#13131a] border border-[#2a2a35] rounded-xl p-6 mb-8">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Full Name" id="name" placeholder="Jane Smith" />
        <Field label="Email" id="email" type="email" placeholder="jane@example.com" />
        <Field label="Company" id="company" placeholder="Google" />
        <Field label="Job Title" id="title" placeholder="Software Engineer" />
        <Field label="Level" id="level" placeholder="L5" />
        <Field label="Location" id="location" placeholder="Mountain View, CA" />
        <Field label="Years of Experience" id="years_of_experience" type="number" placeholder="6" />
        <Field label="Base Salary ($)" id="base_salary" type="number" placeholder="180000" />
        <Field label="Bonus ($)" id="bonus" type="number" placeholder="30000" />
        <Field label="Stock / RSU ($)" id="stock_rsu" type="number" placeholder="200000" />
        <div className="col-span-2">
          <Field label="Total Compensation ($)" id="total_compensation" type="number" placeholder="410000" />
        </div>
      </div>

      {error && <p className="mt-4 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3">{error}</p>}

      <button
        onClick={submit} disabled={loading}
        className="mt-5 w-full py-2.5 bg-violet-600 hover:bg-violet-700 disabled:bg-[#2a2a35] disabled:text-zinc-600 text-white text-sm font-semibold rounded-lg transition-colors tracking-wide"
      >
        {loading ? "Validating..." : "Validate Submission →"}
      </button>

      <ResultPanel data={result} />
    </div>
  );
}

function DetailPanel({ submission, onClose }) {
  if (!submission) return null;
  const s = submission;
  const fields = [
    ["Location", s.location], ["Experience", `${s.years_of_experience} yrs`],
    ["Base Salary", `$${(s.base_salary || 0).toLocaleString()}`], ["Bonus", `$${(s.bonus || 0).toLocaleString()}`],
    ["RSU", `$${(s.stock_rsu || 0).toLocaleString()}`], ["Total Comp", `$${(s.total_compensation || 0).toLocaleString()}`],
    ["Rule Score", s.rule_score ?? "—"], ["AI Score", s.ai_score ?? "—"],
  ];
  return (
    <div className="border-t border-[#2a2a35] mt-2 pt-5 px-5 pb-5">
      <div className="flex justify-between items-center mb-4">
        <p className="text-sm font-semibold text-zinc-200">{s.name} <span className="text-violet-400">@ {s.company}</span></p>
        <button onClick={onClose} className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">✕ close</button>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        {fields.map(([label, val]) => (
          <div key={label} className="bg-[#0d0d0f] rounded-lg px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wider text-zinc-600">{label}</p>
            <p className="text-sm text-zinc-200 mt-1 font-mono">{val}</p>
          </div>
        ))}
      </div>
      {s.flags?.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">Flags</p>
          {s.flags.map((f, i) => <FlagItem key={i} flag={f} />)}
        </div>
      ) : (
        <p className="text-xs text-zinc-600">No flags — submission passed all checks.</p>
      )}
    </div>
  );
}

function SubmissionsTable({ submissions, loading }) {
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);

  const filtered = submissions.filter(s =>
    filter === "all" ? true : filter === "passed" ? s.passed : !s.passed
  );

  const toggleRow = (s) => setSelected(prev => prev?.id === s.id ? null : s);

  return (
    <div className="bg-[#13131a] border border-[#2a2a35] rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#2a2a35]">
        <p className="text-[10px] uppercase tracking-widest text-zinc-600">All Submissions</p>
        <div className="flex gap-1">
          {["all", "passed", "flagged"].map(f => (
            <button key={f} onClick={() => { setFilter(f); setSelected(null); }}
              className={`text-[11px] px-3 py-1 rounded-full border transition-all ${filter === f ? "bg-[#1a1a28] border-violet-500/50 text-violet-400" : "border-[#2a2a35] text-zinc-600 hover:text-zinc-400"}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-center text-zinc-600 text-xs py-12">Loading submissions...</p>
      ) : filtered.length === 0 ? (
        <p className="text-center text-zinc-600 text-xs py-12">No submissions found. Submit one above to get started.</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#2a2a35]">
              {["Name", "Company", "Title", "Level", "Score", "Confidence", "Status"].map(h => (
                <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-zinc-600 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => (
              <>
                <tr key={s.id} onClick={() => toggleRow(s)}
                  className={`border-b border-[#1a1a25] cursor-pointer transition-colors ${selected?.id === s.id ? "bg-[#16161f]" : "hover:bg-[#16161f]"}`}>
                  <td className="px-4 py-3 text-zinc-200 font-medium">{s.name}</td>
                  <td className="px-4 py-3 text-violet-400">{s.company}</td>
                  <td className="px-4 py-3 text-zinc-500">{s.title}</td>
                  <td className="px-4 py-3 text-zinc-500">{s.level}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded border text-xs font-semibold ${scoreBg(s.overall_score)} ${scoreColor(s.overall_score)}`}>
                      {s.overall_score ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full border text-[10px] ${confidenceBadge(s.confidence_level)}`}>
                      {s.confidence_level || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${s.passed ? "bg-emerald-400" : "bg-red-400"}`} />
                      <span className={s.passed ? "text-emerald-400" : "text-red-400"}>{s.passed ? "Passed" : "Flagged"}</span>
                    </span>
                  </td>
                </tr>
                {selected?.id === s.id && (
                  <tr key={`detail-${s.id}`}>
                    <td colSpan={7} className="bg-[#0d0d0f]">
                      <DetailPanel submission={selected} onClose={() => setSelected(null)} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function App() {
  const [stats, setStats] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loadingTable, setLoadingTable] = useState(true);
  const [apiStatus, setApiStatus] = useState("connecting");

  const loadStats = async () => {
    try {
      const r = await fetch(`${API}/dashboard/stats/`);
      if (!r.ok) throw new Error();
      setStats(await r.json());
      setApiStatus("online");
    } catch {
      setApiStatus("offline");
    }
  };

  const loadSubmissions = async () => {
    setLoadingTable(true);
    try {
      const r = await fetch(`${API}/submissions/`);
      if (!r.ok) throw new Error();
      setSubmissions(await r.json());
    } catch {
      setSubmissions([]);
    } finally {
      setLoadingTable(false);
    }
  };

  const refresh = useCallback(() => {
    loadStats();
    loadSubmissions();
  }, []);

  useEffect(() => { refresh(); }, []);

  return (
    <div className="min-h-screen bg-[#0d0d0f] text-zinc-200 font-mono">
      <div className="max-w-5xl mx-auto px-6 py-10">

        <div className="flex items-center gap-3 mb-10 pb-6 border-b border-[#2a2a35]">
          <div className="w-9 h-9 bg-violet-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">SV</div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Salary Validator</h1>
            <p className="text-xs text-zinc-600">Levels.fyi · Crowdsourced Data Validation System</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${apiStatus === "online" ? "bg-emerald-400" : apiStatus === "offline" ? "bg-red-400" : "bg-amber-400"}`} />
            <span className="text-[11px] text-zinc-600">{apiStatus}</span>
            <button onClick={refresh} className="ml-3 text-[11px] px-3 py-1 rounded-full border border-[#2a2a35] text-zinc-600 hover:text-zinc-400 transition-colors">↻ Refresh</button>
          </div>
        </div>

        <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-4">Overview</p>
        <div className="grid grid-cols-4 gap-3 mb-10">
          <StatCard label="Total" value={stats?.total_submissions} color="text-violet-400" />
          <StatCard label="Passed" value={stats?.passed} color="text-emerald-400" />
          <StatCard label="Flagged" value={stats?.flagged} color="text-red-400" />
          <StatCard label="Avg Score" value={stats?.average_score != null ? Math.round(stats.average_score) : null} color="text-amber-400" />
        </div>

        <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-4">New Submission</p>
        <SubmissionForm onSubmitted={refresh} />

        <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-4">Submissions</p>
        <SubmissionsTable submissions={submissions} loading={loadingTable} />

      </div>
    </div>
  );
}
