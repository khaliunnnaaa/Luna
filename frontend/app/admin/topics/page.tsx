"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { api, Topic } from "@/lib/api";

type Form = { id: string; name: string; grade: number; description: string; prerequisites: string[] };

const EMPTY: Form = { id: "", name: "", grade: 10, description: "", prerequisites: [] };

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => setTopics(await api.get<Topic[]>("/admin/topics")), []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  const nameOf = (id: string) => topics.find((t) => t.id === id)?.name ?? id;

  function startEdit(t: Topic) {
    setError("");
    setEditing(true);
    setForm({ ...t, description: t.description ?? "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function togglePrereq(id: string) {
    if (!form) return;
    const has = form.prerequisites.includes(id);
    setForm({
      ...form,
      prerequisites: has ? form.prerequisites.filter((p) => p !== id) : [...form.prerequisites, id],
    });
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setError("");
    const body = { ...form, description: form.description || null };
    try {
      if (editing) await api.put(`/admin/topics/${form.id}`, body);
      else await api.post("/admin/topics", body);
      setForm(null);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDelete(t: Topic) {
    if (!window.confirm(`"${t.name}" сэдвийг устгах уу?`)) return;
    try {
      await api.del(`/admin/topics/${t.id}`);
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
            setEditing(false);
            setForm({ ...EMPTY });
          }}
        >
          + Шинэ сэдэв
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {form && (
        <form className="panel form" onSubmit={onSave}>
          <label>
            ID (латин, жишээ: quadratic_eq)
            <input
              value={form.id}
              onChange={(e) => setForm({ ...form, id: e.target.value })}
              disabled={editing}
              required
            />
          </label>
          <label>
            Нэр
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Анги
            <select value={form.grade} onChange={(e) => setForm({ ...form, grade: Number(e.target.value) })}>
              {[9, 10, 11, 12, 13, 14].map((g) => (
                <option key={g} value={g}>
                  {g <= 12 ? `${g}-р анги` : `Их сургууль ${g - 12}-р курс`}
                </option>
              ))}
            </select>
          </label>
          <label>
            Тайлбар (заавал биш)
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className="full">
            <span className="hint">Өмнө нь заавал мэдэх ёстой сэдвүүд:</span>
            <div className="checks" style={{ marginTop: 8 }}>
              {topics
                .filter((t) => t.id !== form.id)
                .map((t) => (
                  <label key={t.id} className="check">
                    <input
                      type="checkbox"
                      checked={form.prerequisites.includes(t.id)}
                      onChange={() => togglePrereq(t.id)}
                    />
                    {t.name}
                  </label>
                ))}
              {topics.length === 0 && <span className="hint">Одоогоор өөр сэдэв алга.</span>}
            </div>
          </div>
          <div className="actions">
            <button type="button" className="btn secondary small" onClick={() => setForm(null)}>
              Болих
            </button>
            <button type="submit" className="btn small">
              {editing ? "Хадгалах" : "Нэмэх"}
            </button>
          </div>
        </form>
      )}

      <div className="list">
        {topics.length === 0 && <div className="empty">Сэдэв алга байна.</div>}
        {topics.map((t) => (
          <div key={t.id} className="item">
            <div className="item-main">
              <strong>{t.name}</strong>
              <div className="item-meta">
                <span>{t.id}</span>
                <span>{t.grade <= 12 ? `${t.grade}-р анги` : `${t.grade - 12}-р курс`}</span>
                <span>{t.problem_count} бодлого</span>
                <span>
                  Өмнөх: {t.prerequisites.length ? t.prerequisites.map(nameOf).join(", ") : "—"}
                </span>
              </div>
            </div>
            <div className="item-actions">
              <button className="btn secondary small" onClick={() => startEdit(t)}>
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
