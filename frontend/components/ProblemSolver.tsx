"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import MathText from "@/components/MathText";
import { api, AttemptResult, DIFFICULTY_LABEL, Hint, ProblemStudent, TermPublic } from "@/lib/api";

type Props = {
  problem: ProblemStudent;
  reason?: string; // FR-09: яагаад энэ бодлогыг санал болгосон
  onNext?: () => void; // "Дараагийн бодлого" дарахад
};

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

  const pct = (x: number) => Math.round(x * 100);

  return (
    <div className="solver">
      {reason && <p className="reason">💡 {reason}</p>}

      <div className="solver-head">
        <span className="badge">{problem.topic_name}</span>
        <span className="badge muted">
          {problem.difficulty} · {DIFFICULTY_LABEL[problem.difficulty]}
        </span>
        {problem.subtopic && <span className="badge muted">{problem.subtopic}</span>}
        {solved && <span className="badge ok">✓ бодсон</span>}
      </div>

      <div className="statement">
        <TermHighlighter text={problem.statement} terms={highlight} onTerm={showTerm} />
      </div>
      <p className="hint">Ойлгохгүй үг дээрээ дарвал тайлбар гарна.</p>

      {term && (
        <div className="term-box">
          <strong>{term.term}</strong>
          {term.explanation ? (
            <>
              <p>{term.explanation}</p>
              {term.example && (
                <p className="hint">
                  Жишээ: <MathText text={term.example} />
                </p>
              )}
            </>
          ) : (
            <p className="hint">Энэ үгийн тайлбар толинд хараахан алга. Бүртгэж авлаа.</p>
          )}
          <button type="button" className="link" onClick={() => setTerm(null)}>
            хаах
          </button>
        </div>
      )}

      {hints.length > 0 && (
        <ol className="hints">
          {hints.map((h) => (
            <li key={h.level}>
              <MathText text={h.hint} />
            </li>
          ))}
        </ol>
      )}

      {!result?.is_correct && hints.length < problem.hint_count && (
        <button type="button" className="btn secondary small" onClick={nextHint}>
          {hints.length === 0 ? "Сануулга авах" : `Дараагийн сануулга (${hints.length + 1}/${problem.hint_count})`}
        </button>
      )}

      <form onSubmit={submit} className="answer-form">
        <div className="field">
          <label htmlFor="answer">Таны хариу</label>
          <input
            id="answer"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="жишээ: 3, 1/2, [3, 4], 2*sqrt(2)"
            autoComplete="off"
            disabled={busy}
          />
          <span className="hint">
            Олон шийдтэй бол [3, 4], цэг бол (2, -3) гэж бич. x^2, sqrt(2), pi ашиглаж болно.
          </span>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="btn" disabled={busy || !answer.trim()}>
          {busy ? "Шалгаж байна..." : "Шалгах"}
        </button>
      </form>

      {result && (
        <div className={`result ${result.is_correct ? "ok" : "bad"}`}>
          <p className="result-text">{result.feedback}</p>
          <p className="hint">
            Оролдлого: {attempts} · {problem.topic_name} эзэмшил {pct(result.mastery_before)}% →{" "}
            <strong>{pct(result.mastery_after)}%</strong>
          </p>
          <div className="bar">
            <div className="bar-fill" style={{ width: `${pct(result.mastery_after)}%` }} />
          </div>
          {result.is_correct && onNext && (
            <button type="button" className="btn" onClick={onNext} style={{ marginTop: 12 }}>
              Дараагийн бодлого →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
