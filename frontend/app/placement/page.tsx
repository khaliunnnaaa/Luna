"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { SyntheticEvent, useCallback, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import { api, DIFFICULTY_LABEL, getToken, PlacementAnswer, PlacementState } from "@/lib/api";

// FR-02: 8–10 асуулттай, 10 минутаас хэтрэхгүй adaptive тест.
export default function PlacementPage() {
  const router = useRouter();
  const [state, setState] = useState<PlacementState | null>(null);
  const [answer, setAnswer] = useState("");
  const [last, setLast] = useState<PlacementAnswer | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await api.get<PlacementState>("/placement");
      setState(s);
      setLeft(s.seconds_left);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [load, router]);

  // Цаг тоолуур; 0 болоход backend-д дуусгана
  useEffect(() => {
    if (state?.status !== "active" || left === null) return;
    if (left <= 0) {
      api.post<PlacementState>("/placement/finish", {}).then(setState).catch(() => load());
      return;
    }
    const t = setTimeout(() => setLeft(left - 1), 1000);
    return () => clearTimeout(t);
  }, [left, state?.status, load]);

  async function start() {
    setError("");
    setLast(null);
    setBusy(true);
    try {
      const s = await api.post<PlacementState>("/placement/start", {});
      setState(s);
      setLeft(s.seconds_left);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: SyntheticEvent, text: string) {
    e.preventDefault();
    if (!state?.question) return;
    setError("");
    setBusy(true);
    try {
      const r = await api.post<PlacementAnswer>("/placement/answer", {
        problem_id: state.question.problem_id,
        answer: text,
      });
      setLast(r);
      setState(r.state);
      setAnswer("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  const pct = (x: number) => Math.round(x * 100);

  return (
    <main className="student">
      <div className="student-top">
        <Link href="/dashboard" className="link">
          ← Самбар
        </Link>
        <h1>Түвшин тогтоох тест</h1>
      </div>
      {error && <div className="error">{error}</div>}
      {!state && !error && <p className="subtitle">Ачаалж байна...</p>}

      {state?.status === "none" && (
        <div className="card wide">
          <h2>Хаанаас эхлэхээ мэдье</h2>
          <p>
            8–10 богино асуулт, 10 минутаас хэтрэхгүй. Мэдэхгүй бол «Мэдэхгүй» гэж дарахад болно —
            энэ нь шалгалт биш, зөвхөн хаанаас эхлэхийг тогтооно.
          </p>
          <button className="btn" onClick={start} disabled={busy}>
            Эхлэх
          </button>
        </div>
      )}

      {state?.status === "active" && state.question && (
        <div className="card wide">
          <div className="placement-top">
            <span className="badge">
              {state.index + 1} / {state.total}
            </span>
            <span className="badge muted">{state.question.topic_name}</span>
            <span className="badge muted">{DIFFICULTY_LABEL[state.question.difficulty]}</span>
            {left !== null && <span className={`timer ${left < 60 ? "warn" : ""}`}>⏱ {mmss(left)}</span>}
          </div>
          <div className="bar" style={{ margin: "12px 0 18px" }}>
            <div className="bar-fill" style={{ width: `${(state.index / state.total) * 100}%` }} />
          </div>

          {last && (
            <p className={`placement-feedback ${last.correct ? "ok" : ""}`}>{last.feedback}</p>
          )}

          <div className="statement">
            <MathText text={state.question.statement} />
          </div>

          <form onSubmit={(e) => submit(e, answer)} className="answer-form" style={{ marginTop: 16 }}>
            <div className="field">
              <label htmlFor="answer">Хариу</label>
              <input
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="жишээ: 3, 1/2, [3, 4]"
                autoComplete="off"
                disabled={busy}
              />
            </div>
            <div className="row">
              <button className="btn" disabled={busy || !answer.trim()}>
                Хариулах
              </button>
              <button
                type="button"
                className="btn secondary"
                disabled={busy}
                onClick={(e) => submit(e, "")}
              >
                Мэдэхгүй
              </button>
            </div>
          </form>
        </div>
      )}

      {state?.status === "done" && (
        <div className="card wide">
          <h2>Үр дүн</h2>
          <p className="subtitle">
            {state.correct_count} / {state.index} зөв. Сэдэв бүрийн эхлэх түвшин тогтлоо — одоо
            дасгалаа эндээс эхэлнэ.
          </p>
          <ul className="mastery-list">
            {state.result.map((r) => (
              <li key={r.topic_id} className="mastery-row static">
                <div className="mastery-name">
                  <span>{r.topic_name}</span>
                  <span className="hint">
                    түвшин {r.difficulty} · {r.correct ? "зөв ✓" : "буруу ✗"}
                  </span>
                </div>
                <div className="bar">
                  <div className="bar-fill" style={{ width: `${pct(r.p_mastery)}%` }} />
                </div>
                <span className="mastery-pct">{pct(r.p_mastery)}%</span>
              </li>
            ))}
          </ul>
          <div className="row" style={{ marginTop: 18 }}>
            <Link href="/practice" className="btn">
              Дасгал эхлэх →
            </Link>
            <button className="btn secondary" onClick={start} disabled={busy}>
              Дахин өгөх
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
