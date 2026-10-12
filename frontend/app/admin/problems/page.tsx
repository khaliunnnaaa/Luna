"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import { api, Problem, Topic } from "@/lib/api";

type Form = {
  code: string;
  topic_id: string;
  subtopic: string;
  difficulty: number;
  statement: string;
  answers: string; // мөр бүрт нэг хариу
  hints: [string, string, string];
  solution_steps: string; // мөр бүрт нэг алхам (FR-07)
  common_mistakes: string;
  terms: string; // ";"-ээр тусгаарлана
  source: string;
};

const EMPTY: Form = {
  code: "",
  topic_id: "",
  subtopic: "",
  difficulty: 1,
  statement: "",
  answers: "",
  hints: ["", "", ""],
  solution_steps: "",
  common_mistakes: "",
  terms: "",
  source: "",
};

const LEVELS: Record<number, string> = { 1: "1 · хялбар", 2: "2 · дунд", 3: "3 · хүнд" };

const HINT_LABELS = ["1. Чиглүүлэх асуулт", "2. Арга", "3. Эхний алхам"];

function toForm(p: Problem): Form {
  const h = [...p.hints, "", "", ""];
  return {
    code: p.code ?? "",
    topic_id: p.topic_id,
    subtopic: p.subtopic ?? "",
    difficulty: p.difficulty,
    statement: p.statement,
    answers: p.answers.join("\n"),
    hints: [h[0], h[1], h[2]],
    solution_steps: (p.solution_steps ?? []).join("\n"),
    common_mistakes: p.common_mistakes ?? "",
    terms: p.terms.join("; "),
    source: p.source ?? "",
  };
}

export default function ProblemsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState<Form | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const q = filter ? `?topic_id=${encodeURIComponent(filter)}` : "";
    const [t, p] = await Promise.all([
      api.get<Topic[]>("/admin/topics"),
      api.get<Problem[]>(`/admin/problems${q}`),
    ]);
    setTopics(t);
    setProblems(p);
  }, [filter]);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  const topicName = (id: string) => topics.find((t) => t.id === id)?.name ?? id;

  function startNew() {
    setError("");
    setEditingId(null);
    setForm({ ...EMPTY, topic_id: filter || topics[0]?.id || "" });
  }

  function startEdit(p: Problem) {
    setError("");
    setEditingId(p.id);
    setForm(toForm(p));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError("");
    const body = {
      code: form.code || null,
      topic_id: form.topic_id,
      subtopic: form.subtopic || null,
      difficulty: form.difficulty,
      statement: form.statement,
      answers: form.answers.split("\n"),
      hints: form.hints,
      solution_steps: form.solution_steps.split("\n"),
      common_mistakes: form.common_mistakes || null,
      terms: form.terms.split(";"),
      source: form.source || null,
    };
    try {
      if (editingId) await api.put(`/admin/problems/${editingId}`, body);
      else await api.post("/admin/problems", body);
      setForm(null);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(p: Problem) {
    if (!window.confirm("Энэ бодлогыг устгах уу?")) return;
    try {
      await api.del(`/admin/problems/${p.id}`);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const set = <K extends keyof Form>(k: K, v: Form[K]) => form && setForm({ ...form, [k]: v });

  return (
    <>
      <div className="toolbar">
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">Бүх сэдэв</option>
          {topics.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.problem_count})
            </option>
          ))}
        </select>
        <button className="btn small" onClick={startNew} disabled={topics.length === 0}>
          + Шинэ бодлого
        </button>
        {topics.length === 0 && <span className="hint">Эхлээд &quot;Сэдэв&quot; хэсэгт сэдэв нэмнэ үү.</span>}
      </div>

      {error && <div className="error">{error}</div>}

      {form && (
        <form className="panel form" onSubmit={onSave}>
          <label>
            Сэдэв
            <select value={form.topic_id} onChange={(e) => set("topic_id", e.target.value)} required>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Хүндийн зэрэг
            <select value={form.difficulty} onChange={(e) => set("difficulty", Number(e.target.value))}>
              {[1, 2, 3].map((d) => (
                <option key={d} value={d}>
                  {LEVELS[d]}
                </option>
              ))}
            </select>
          </label>

          <label className="full">
            Бодлогын текст (томьёог $...$ дотор бичнэ)
            <textarea
              value={form.statement}
              onChange={(e) => set("statement", e.target.value)}
              placeholder="Тэгшитгэлийг бод: $x^2 - 5x + 6 = 0$"
              required
            />
          </label>
          <div className="full">
            <span className="hint">Урьдчилан харах:</span>
            <div className="preview">
              <MathText text={form.statement || "…"} />
            </div>
          </div>

          <label className="full">
            {"Зөв хариу (SymPy хэлбэр, жишээ: 1/2 · [3, 4] · {x: 7, y: 3} · Interval(2, oo))"}
            <textarea
              value={form.answers}
              onChange={(e) => set("answers", e.target.value)}
              placeholder={"2\n3"}
              style={{ minHeight: 60 }}
              required
            />
          </label>

          {HINT_LABELS.map((label, i) => (
            <label key={i} className="full">
              Сануулга {label}
              <input
                value={form.hints[i]}
                onChange={(e) => {
                  const h = [...form.hints] as Form["hints"];
                  h[i] = e.target.value;
                  set("hints", h);
                }}
              />
            </label>
          ))}

          <label className="full">
            Бодолтын алхмууд — мөр бүрт нэг (FR-07: ижил төстэй бодлогоор тайлбарлахад харуулна)
            <textarea
              value={form.solution_steps}
              onChange={(e) => set("solution_steps", e.target.value)}
              placeholder={"Виет: үржвэр 12, нийлбэр 7.\n$3 \\cdot 4 = 12$, $3 + 4 = 7$.\n$x = 3$; $x = 4$."}
              rows={4}
            />
          </label>

          <label className="full">
            Түгээмэл алдаа (заавал биш)
            <input
              value={form.common_mistakes}
              onChange={(e) => set("common_mistakes", e.target.value)}
              placeholder="Илтгэгчийг үржүүлэх: 2^6 = 64"
            />
          </label>
          <label>
            Дэд сэдэв (заавал биш)
            <input value={form.subtopic} onChange={(e) => set("subtopic", e.target.value)} />
          </label>
          <label>
            Нэр томьёо (; -ээр тусгаарлана)
            <input
              value={form.terms}
              onChange={(e) => set("terms", e.target.value)}
              placeholder="зэрэг; илтгэгч"
            />
          </label>
          <label>
            Код (заавал биш)
            <input value={form.code} onChange={(e) => set("code", e.target.value)} placeholder="T04-031" />
          </label>
          <label>
            Эх сурвалж (заавал биш)
            <input
              value={form.source}
              onChange={(e) => set("source", e.target.value)}
              placeholder="ЭЕШ 2023, B хувилбар"
            />
          </label>

          <div className="actions">
            <button type="button" className="btn secondary small" onClick={() => setForm(null)}>
              Болих
            </button>
            <button type="submit" className="btn small" disabled={saving}>
              {saving ? "Хадгалж байна..." : editingId ? "Хадгалах" : "Нэмэх"}
            </button>
          </div>
        </form>
      )}

      <div className="list">
        {problems.length === 0 && <div className="empty">Бодлого алга байна.</div>}
        {problems.map((p) => (
          <div key={p.id} className="item">
            <div className="item-main">
              <MathText text={p.statement} />
              <div className="item-meta">
                <span>{topicName(p.topic_id)}</span>
                {p.subtopic && <span>{p.subtopic}</span>}
                <span>Түвшин: {LEVELS[p.difficulty] ?? p.difficulty}</span>
                <span>Хариу: {p.answers.join(", ")}</span>
                <span>Сануулга: {p.hints.length}/3</span>
                <span>Алхам: {p.solution_steps?.length ?? 0}</span>
                {p.code && <span>#{p.code}</span>}
              </div>
            </div>
            <div className="item-actions">
              <button className="btn secondary small" onClick={() => startEdit(p)}>
                Засах
              </button>
              <button className="btn danger small" onClick={() => onDelete(p)}>
                Устгах
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
