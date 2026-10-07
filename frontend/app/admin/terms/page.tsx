"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import { api, Term, Topic } from "@/lib/api";

type Form = { term: string; explanation: string; example: string; topic_id: string };

const EMPTY: Form = { term: "", explanation: "", example: "", topic_id: "" };

export default function TermsPage() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [te, to] = await Promise.all([
      api.get<Term[]>("/admin/terms"),
      api.get<Topic[]>("/admin/topics"),
    ]);
    setTerms(te);
    setTopics(to);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setError("");
    const body = { ...form, example: form.example || null, topic_id: form.topic_id || null };
    try {
      if (editingId) await api.put(`/admin/terms/${editingId}`, body);
      else await api.post("/admin/terms", body);
      setForm(null);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDelete(t: Term) {
    if (!window.confirm(`"${t.term}" нэр томьёог устгах уу?`)) return;
    try {
      await api.del(`/admin/terms/${t.id}`);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <>
      <div className="toolbar">
        <button
          className="btn small"
          onClick={() => {
            setError("");
            setEditingId(null);
            setForm({ ...EMPTY });
          }}
        >
          + Шинэ нэр томьёо
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {form && (
        <form className="panel form" onSubmit={onSave}>
          <label>
            Нэр томьёо
            <input value={form.term} onChange={(e) => setForm({ ...form, term: e.target.value })} required />
          </label>
          <label>
            Сэдэв
            <select value={form.topic_id} onChange={(e) => setForm({ ...form, topic_id: e.target.value })}>
              <option value="">— Сонгоогүй —</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="full">
            Энгийн тайлбар (2–3 өгүүлбэр)
            <textarea
              value={form.explanation}
              onChange={(e) => setForm({ ...form, explanation: e.target.value })}
              required
            />
          </label>
          <label className="full">
            Жишээ (заавал биш, томьёог $...$ дотор)
            <input value={form.example} onChange={(e) => setForm({ ...form, example: e.target.value })} />
          </label>
          <div className="actions">
            <button type="button" className="btn secondary small" onClick={() => setForm(null)}>
              Болих
            </button>
            <button type="submit" className="btn small">
              {editingId ? "Хадгалах" : "Нэмэх"}
            </button>
          </div>
        </form>
      )}

      <div className="list">
        {terms.length === 0 && <div className="empty">Нэр томьёо алга байна.</div>}
        {terms.map((t) => (
          <div key={t.id} className="item">
            <div className="item-main">
              <strong>{t.term}</strong>
              <div style={{ marginTop: 4 }}>{t.explanation}</div>
              {t.example && (
                <div className="item-meta">
                  <span>
                    Жишээ: <MathText text={t.example} />
                  </span>
                </div>
              )}
            </div>
            <div className="item-actions">
              <button
                className="btn secondary small"
                onClick={() => {
                  setError("");
                  setEditingId(t.id);
                  setForm({
                    term: t.term,
                    explanation: t.explanation,
                    example: t.example ?? "",
                    topic_id: t.topic_id ?? "",
                  });
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                Засах
              </button>
              <button className="btn danger small" onClick={() => onDelete(t)}>
                Устгах
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
