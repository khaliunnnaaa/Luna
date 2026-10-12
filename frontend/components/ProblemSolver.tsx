"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import MathText from "@/components/MathText";
import { api, AttemptResult, DIFFICULTY_LABEL, Hint, ProblemStudent, TermPublic } from "@/lib/api";

type Props = {
  problem: ProblemStudent;
  reason?: string; // FR-09: яагаад энэ бодлогыг санал болгосон
  onNext?: () => void; // "Дараагийн бодлого" дарахад
};

// Сануулгын 3 шат: онол → арга → анхаарах зүйл (ml/tools/bank_hints.py)
const HINT_LABEL: Record<number, string> = { 1: "Онол", 2: "Арга", 3: "Анхаар" };

// Хариуны талбарт хурдан оруулах тэмдэгтүүд (SymPy хэлбэр)
const SNIPPETS = [
  { label: "√", insert: "sqrt()", title: "Квадрат язгуур: sqrt(2)" },
  { label: "x²", insert: "^2", title: "Зэрэг: x^2" },
  { label: "π", insert: "pi", title: "Пи тоо" },
  { label: "a/b", insert: "/", title: "Бутархай: 1/2" },
  { label: "[ , ]", insert: "[, ]", title: "Олон шийд: [3, 4]" },
  { label: "( , )", insert: "(, )", title: "Цэг: (2, -3)" },
  { label: "−", insert: "-", title: "Хасах" },
];

// Бодлогын өгүүлбэр дэх нэр томьёог дарж болохоор тодруулна (FR-05).
// Томьёо ($...$) хэсэгт хүрэхгүй.
function TermHighlighter({
  text,
  terms,
  onTerm,
}: {
  text: string;
  terms: string[];
  onTerm: (t: string) => void;
}) {
  const parts = text.split(/(\$[^$]+\$)/g);
  // split-д global, шалгахад анхорлосон (g флагийн lastIndex-ийн алдаанаас сэргийлнэ)
  const regs = useMemo(() => {
    const sorted = [...terms].filter(Boolean).sort((a, b) => b.length - a.length);
    if (sorted.length === 0) return null;
    const esc = sorted.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
    return { split: new RegExp(`(${esc})`, "gi"), test: new RegExp(`^(${esc})$`, "i") };
  }, [terms]);

  return (
    <span>
      {parts.map((part, i) => {
        if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
          return <MathText key={i} text={part} />;
        }
        if (!regs) return <span key={i}>{part}</span>;
        return (
          <span key={i}>
            {part.split(regs.split).map((piece, j) =>
              regs.test.test(piece) ? (
                <button
                  key={j}
                  type="button"
                  className="term"
                  title="Тайлбар харах"
                  onClick={() => onTerm(piece)}
                >
                  {piece}
                </button>
              ) : (
                <span key={j}>{piece}</span>
              ),
            )}
          </span>
        );
      })}
    </span>
  );
}

export default function ProblemSolver({ problem, reason, onNext }: Props) {
  const [answer, setAnswer] = useState("");
  const [hints, setHints] = useState<Hint[]>([]);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [attempts, setAttempts] = useState(problem.my_attempts);
  const [solved, setSolved] = useState(problem.solved);
  const [glossary, setGlossary] = useState<TermPublic[]>([]);
  const [term, setTerm] = useState<{ term: string; explanation: string | null; example: string | null } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Бодлого солигдоход төлөвийг цэвэрлэнэ
  useEffect(() => {
    setAnswer("");
    setHints([]);
    setResult(null);
    setTerm(null);
    setError("");
    setAttempts(problem.my_attempts);
    setSolved(problem.solved);
  }, [problem.id, problem.my_attempts, problem.solved]);

  useEffect(() => {
    api.get<TermPublic[]>("/terms").then(setGlossary).catch(() => {});
  }, []);

  // Өгүүлбэрт тодруулах үгс: бодлогын terms + толинд байгаа бүх үг
  const highlight = useMemo(
    () => Array.from(new Set([...problem.terms, ...glossary.map((g) => g.term)])),
    [problem.terms, glossary],
  );

  async function showTerm(t: string) {
    const local = glossary.find((g) => g.term.toLowerCase() === t.toLowerCase());
    setTerm({ term: t, explanation: local?.explanation ?? null, example: local?.example ?? null });
    // Сул талын дохио болгон бүртгэнэ (FR-05/08); алдаа гарвал чимээгүй өнгөрөөнө
    api.post("/term-clicks", { term: t, problem_id: problem.id }).catch(() => {});
  }

  async function nextHint() {
    const level = hints.length + 1;
    if (level > problem.hint_count) return;
    setError("");
    try {
      const h = await api.get<Hint>(`/problems/${problem.id}/hints/${level}`);
      setHints((prev) => [...prev, h]);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const r = await api.post<AttemptResult>(`/problems/${problem.id}/attempt`, {
        answer,
        hints_used: hints.length,
      });
      setResult(r);
      setAttempts(r.attempts_on_problem);
      if (r.is_correct) setSolved(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  // Хариу бичихэд хэрэгтэй тэмдэгтүүдийг курсорын байрлалд оруулна
  function insert(snippet: string) {
    const el = inputRef.current;
    if (!el) return setAnswer((a) => a + snippet);
    const start = el.selectionStart ?? answer.length;
    const end = el.selectionEnd ?? answer.length;
    const next = answer.slice(0, start) + snippet + answer.slice(end);
    setAnswer(next);
    // "sqrt()" бол хаалтын дотор, "[, ]" бол эхний элементийн байранд курсор тавина
    const offset = snippet.includes(",")
      ? snippet.indexOf(",")
      : snippet.endsWith("()")
        ? snippet.length - 1
        : snippet.length;
    const caret = start + offset;
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(caret, caret);
    });
  }

  const pct = (x: number) => Math.round(x * 100);
  const hintsLeft = problem.hint_count - hints.length;

  return (
    <div className="solver">
      {reason && <p className="reason">{reason}</p>}

      <div className="card question">
        <div className="indexline">
          <span>{problem.code ? `Бодлого ${problem.code}` : "Бодлого"}</span>
          <span className="tags">
            <span className="badge">{problem.topic_name}</span>
            <span className="badge muted">{DIFFICULTY_LABEL[problem.difficulty]}</span>
            {solved && <span className="badge ok">✓ бодсон</span>}
          </span>
        </div>

        <div className="solver" style={{ marginTop: 22 }}>
          <div className="statement">
            <TermHighlighter text={problem.statement} terms={highlight} onTerm={showTerm} />
          </div>
          {highlight.length > 0 && (
            <p className="hint" style={{ margin: 0 }}>
              Тасархай зураастай үг дээр дарвал тайлбар гарна.
            </p>
          )}

          {term && (
            <div className="term-box" role="note">
              <div className="head">
                <strong>{term.term}</strong>
                <button type="button" className="link" onClick={() => setTerm(null)}>
                  Хаах ✕
                </button>
              </div>
              {term.explanation ? (
                <>
                  <p>
                    <MathText text={term.explanation} />
                  </p>
                  {term.example && (
                    <p className="hint">
                      Жишээ: <MathText text={term.example} />
                    </p>
                  )}
                </>
              ) : (
                <p className="hint">Энэ үгийн тайлбар толинд хараахан алга. Багшид мэдэгдэхээр бүртгэж авлаа.</p>
              )}
            </div>
          )}

          {hints.length > 0 && (
            <ol className="hints" aria-live="polite">
              {hints.map((h) => (
                <li key={h.level}>
                  <span className="hint-label">{HINT_LABEL[h.level] ?? `Сануулга ${h.level}`}</span>
                  <MathText text={h.hint} />
                </li>
              ))}
            </ol>
          )}

          {!result?.is_correct && problem.hint_count > 0 && (
            <div>
              <button
                type="button"
                className="btn light small"
                onClick={nextHint}
                disabled={hintsLeft <= 0}
              >
                {hintsLeft <= 0
                  ? "Сануулга дууссан"
                  : hints.length === 0
                    ? `Сануулга авах (${problem.hint_count} байна)`
                    : `Дараагийн сануулга ${hints.length + 1}/${problem.hint_count}`}
              </button>
            </div>
          )}

          <form onSubmit={submit} className="answer-form answer-box">
            <div className="field">
              <label htmlFor="answer">Таны хариу</label>
              <div className="answer-input">
                <input
                  id="answer"
                  ref={inputRef}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="жишээ: 3, 1/2, [3, 4], 2*sqrt(2)"
                  autoComplete="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  disabled={busy}
                  aria-describedby="answer-help"
                />
                <button className="btn rust" disabled={busy || !answer.trim()}>
                  {busy ? (
                    <>
                      <span className="spinner" aria-hidden /> Шалгаж байна
                    </>
                  ) : (
                    "Шалгах →"
                  )}
                </button>
              </div>
              <div className="chips" aria-label="Тэмдэгт оруулах">
                {SNIPPETS.map((s) => (
                  <button
                    key={s.label}
                    type="button"
                    className="chip"
                    onClick={() => insert(s.insert)}
                    title={s.title}
                    disabled={busy}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <span id="answer-help" className="hint">
                Олон шийдтэй бол [3, 4], цэг бол (2, -3) гэж бичнэ. Enter дарж шалгана.
              </span>
            </div>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
          </form>

          {result && (
            <div className={`result ${result.is_correct ? "ok" : "bad"}`} aria-live="polite">
              <p className="result-text">{result.feedback}</p>
              <p className="hint" style={{ margin: 0 }}>
                {attempts}-р оролдлого · {problem.topic_name}: {pct(result.mastery_before)}% →{" "}
                <strong>{pct(result.mastery_after)}%</strong>
              </p>
              <div className="bar">
                <div className="bar-fill" style={{ width: `${pct(result.mastery_after)}%` }} />
              </div>
              {!result.is_correct && hintsLeft > 0 && (
                <p className="hint" style={{ margin: "8px 0 0" }}>
                  Гацсан бол сануулга аваад дахин оролдоорой — алдаа бол дараагийн алхмын дохио.
                </p>
              )}
              {result.is_correct && onNext && (
                <button type="button" className="btn" onClick={onNext} style={{ marginTop: 14 }} autoFocus>
                  Дараагийн бодлого →
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
