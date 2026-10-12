"use client";

import Link from "next/link";
import { SyntheticEvent, useCallback, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import Shell, { Loading, PageHead } from "@/components/Shell";
import { api, DIFFICULTY_LABEL, getToken, PlacementAnswer, PlacementState } from "@/lib/api";

// FR-02: 8–10 асуулттай, 10 минутаас хэтрэхгүй adaptive тест.
export default function PlacementPage() {
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
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    load();
  }, [load]);

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
    <Shell>
      <Link href="/dashboard" className="back">
        ← Нүүр рүү
      </Link>
      <PageHead eyebrow="Түвшин тогтоох / FR-02" title="Хаанаас эхлэхээ мэдье.">
        8–10 богино асуулт, 10 минутаас хэтрэхгүй. Энэ нь шалгалт биш — зөвхөн дасгалаа хаанаас
        эхлэхийг тогтооно.
      </PageHead>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {!state && !error && <Loading />}

      {state?.status === "none" && (
        <div className="card question">
          <div className="indexline">
            <span>Эхлэхийн өмнө</span>
            <span>≈ 10 минут</span>
          </div>
          <ul className="steps" style={{ margin: "10px 0 26px" }}>
            <li className="step">Сэдэв бүрээс нэг асуулт ирнэ. Зөв хариулбал дараагийнх нь хүндэрнэ.</li>
            <li className="step">Мэдэхгүй бол «Мэдэхгүй» гэж дарахад болно — таамаглах хэрэггүй.</li>
            <li className="step">Дуусахад сэдэв бүрийн эхлэх түвшин тань тогтоно.</li>
          </ul>
          <button className="btn rust" onClick={start} disabled={busy}>
            {busy ? "Бэлдэж байна..." : "Тест эхлэх →"}
          </button>
        </div>
      )}

      {state?.status === "active" && state.question && (
        <div className="card question">
          <div className="indexline">
            <span>
              Асуулт {String(state.index + 1).padStart(2, "0")} / {String(state.total).padStart(2, "0")}
            </span>
            <span className="tags">
              <span className="badge muted">{state.question.topic_name}</span>
              <span className="badge muted">{DIFFICULTY_LABEL[state.question.difficulty]}</span>
              {left !== null && (
                <span className={`timer ${left < 60 ? "warn" : ""}`} aria-label="Үлдсэн хугацаа">
                  {mmss(left)}
                </span>
              )}
            </span>
          </div>
          <div
            className="bar"
            style={{ margin: "0 0 22px" }}
            role="progressbar"
            aria-valuenow={state.index}
            aria-valuemin={0}
            aria-valuemax={state.total}
            aria-label="Тестийн явц"
          >
            <div className="bar-fill" style={{ width: `${(state.index / state.total) * 100}%` }} />
          </div>

          {last && (
            <p className={`placement-feedback ${last.correct ? "ok" : ""}`} aria-live="polite">
              {last.feedback}
            </p>
          )}

          <div className="statement" style={{ margin: "18px 0 22px" }}>
            <MathText text={state.question.statement} />
          </div>

          <form onSubmit={(e) => submit(e, answer)} className="answer-form answer-box">
            <div className="field">
              <label htmlFor="answer">Хариу</label>
              <input
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="жишээ: 3, 1/2, [3, 4]"
                autoComplete="off"
                autoCapitalize="off"
                spellCheck={false}
                disabled={busy}
                autoFocus
                style={{ fontFamily: "var(--serif)", fontSize: 18 }}
              />
              <span className="hint">Олон шийдтэй бол [3, 4], цэг бол (2, -3). x^2, sqrt(2), pi.</span>
            </div>
            <div className="actions">
              <button className="btn rust" disabled={busy || !answer.trim()}>
                Хариулах →
              </button>
              <button type="button" className="btn light" disabled={busy} onClick={(e) => submit(e, "")}>
                Мэдэхгүй
              </button>
            </div>
          </form>
        </div>
      )}

      {state?.status === "done" && (
        <>
          <div className="bottom">
            <div>
              <div className="section-label">
                <h2>Эхлэх түвшин тогтлоо</h2>
              </div>
              <p className="muted" style={{ fontSize: 14, lineHeight: 1.9, maxWidth: 440 }}>
                {state.index} асуултаас {state.correct_count}-д зөв хариуллаа. Сэдэв бүрийн эхлэх түвшин
                тогтлоо — одоо систем танд тохирох дасгалыг эндээс эхлэн санал болгоно.
              </p>
              <div className="actions" style={{ marginTop: 20 }}>
                <Link href="/practice" className="btn rust">
                  Дасгал эхлэх →
                </Link>
                <button className="btn light" onClick={start} disabled={busy}>
                  Дахин өгөх
                </button>
              </div>
            </div>
            <div>
              <div className="section-label">
                <h2>Сэдэв бүрээр</h2>
              </div>
              <ul className="mastery-list">
                {state.result.map((r) => (
                  <li key={r.topic_id} className="mastery-row static">
                    <div className="mastery-name">
                      <span>{r.topic_name}</span>
                      <span className="hint">
                        {DIFFICULTY_LABEL[r.difficulty]} түвшин · {r.correct ? "зөв ✓" : "буруу"}
                      </span>
                    </div>
                    <div className="bar">
                      <div className="bar-fill" style={{ width: `${pct(r.p_mastery)}%` }} />
                    </div>
                    <span className="mastery-pct">{pct(r.p_mastery)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </Shell>
  );
}
