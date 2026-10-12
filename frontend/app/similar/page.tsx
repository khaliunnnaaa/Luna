"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import Shell, { Loading, PageHead } from "@/components/Shell";
import { api, DIFFICULTY_LABEL, getToken, SimilarProblem, UploadDetail } from "@/lib/api";

// FR-07: Сурагчийн бодлогын оронд ижил төстэй бодлогыг алхам алхмаар тайлбарлаж,
// дараа нь сурагч өөрийн бодлогоо бие даан бодно.
//   ?upload=ID            — оруулсан зургийн бодлого (текст, сэдэв upload-оос)
//   ?text=...&topic=T04   — гараар бичсэн бодлого
function Similar() {
  const params = useSearchParams();
  const uploadId = params.get("upload");
  const [own, setOwn] = useState<{ text: string; topic: string | null }>({
    text: params.get("text") ?? "",
    topic: params.get("topic"),
  });
  const [ex, setEx] = useState<SimilarProblem | null>(null);
  const [seen, setSeen] = useState<number[]>([]);
  const [shown, setShown] = useState(0); // нээсэн алхмын тоо
  const [phase, setPhase] = useState<"example" | "own" | "done">("example");
  const [outcome, setOutcome] = useState<"solved" | "unsolved" | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadExample = useCallback(
    async (text: string, topic: string | null, exclude: number[]) => {
      setBusy(true);
      setError("");
      try {
        const r = await api.post<SimilarProblem>("/similar", {
          text,
          topic_id: topic,
          exclude,
        });
        setEx(r);
        setSeen([...exclude, r.problem_id]);
        setShown(0);
        setPhase("example");
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    (async () => {
      let text = own.text;
      let topic = own.topic;
      if (uploadId) {
        try {
          const u = await api.get<UploadDetail>(`/uploads/${uploadId}`);
          text = u.edited_text ?? "";
          topic = topic ?? u.predicted_topic;
          setOwn({ text, topic });
        } catch (e) {
          setError((e as Error).message);
          return;
        }
      }
      if (!text && !topic) {
        setError("Бодлогын текст эсвэл сэдэв байхгүй байна.");
        return;
      }
      loadExample(text, topic, []);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadId]);

  async function setResult(solved: boolean) {
    setOutcome(solved ? "solved" : "unsolved");
    setPhase("done");
    if (uploadId) {
      api.post(`/uploads/${uploadId}/outcome`, { solved }).catch(() => {});
    }
  }

  const topic = ex?.topic_id ?? own.topic;

  return (
    <>
      <Link href="/upload" className="back">
        ← Бодлого оруулах
      </Link>
      <PageHead eyebrow="Хамт бодъё / 03" title="Эхлээд жишээгээр.">
        Ижил төрлийн бодлогыг алхам алхмаар харна. Дараагийн алхмыг нээхээсээ өмнө өөрөө таах гээд
        үзээрэй.
      </PageHead>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {!ex && !error && <Loading label="Ижил төстэй бодлого хайж байна..." />}

      {ex && (
        <div className="card question" style={{ marginBottom: 24 }}>
          <div className="indexline">
            <span>Жишээ бодлого</span>
            <span className="tags">
              <span className="badge">{ex.topic_name}</span>
              <span className="badge muted">{DIFFICULTY_LABEL[ex.difficulty]}</span>
            </span>
          </div>
          {ex.reason && (
            <p className="hint" style={{ margin: "14px 0 0" }}>
              {ex.reason}
            </p>
          )}
          <div className="statement" style={{ margin: "16px 0 8px" }}>
            <MathText text={ex.statement} />
          </div>

          <ol className="steps" aria-live="polite">
            {ex.steps.slice(0, shown).map((s, i) => (
              <li key={i} className="step">
                <MathText text={s} />
              </li>
            ))}
          </ol>

          {phase === "example" && (
            <>
              {shown > 0 && shown < ex.steps.length && (
                <p className="hint" style={{ margin: "14px 0 0" }}>
                  Дараагийн алхам юу байх вэ? Эхлээд өөрөө бодоод, дараа нь нээж шалгаарай.
                </p>
              )}
              <div className="actions" style={{ marginTop: 18 }}>
                {shown < ex.steps.length ? (
                  <button className="btn rust" onClick={() => setShown(shown + 1)}>
                    {shown === 0 ? "Эхний алхмыг харах" : `Дараагийн алхам · ${shown + 1}/${ex.steps.length}`}
                  </button>
                ) : (
                  <button className="btn rust" onClick={() => setPhase("own")}>
                    Ойлголоо — одоо өөрийнхөө бодлогыг бодъё →
                  </button>
                )}
                <button
                  className="btn light"
                  disabled={busy}
                  onClick={() => loadExample(own.text, own.topic, seen)}
                >
                  Өөр жишээ
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {phase !== "example" && (
        <div className="card question">
          <div className="indexline">
            <span>Таны бодлого</span>
            <span>Бие даан</span>
          </div>
          {own.text ? (
            <div className="statement" style={{ margin: "18px 0 10px" }}>
              <MathText text={own.text} />
            </div>
          ) : (
            <p className="hint">Бодлогын текст оруулаагүй — зурган дээрх бодлогоо дэвтэртээ бод.</p>
          )}
          <p className="hint">
            Жишээнийхтэй ижил алхмуудыг өөрийнхөө тоонууд дээр дэвтэртээ хийгээрэй. Систем энэ
            бодлогыг таны өмнөөс бодохгүй.
          </p>
          {phase === "own" && (
            <div className="actions" style={{ marginTop: 18 }}>
              <button className="btn rust" onClick={() => setResult(true)}>
                ✓ Бодож чадлаа
              </button>
              <button className="btn light" onClick={() => setResult(false)}>
                Чадсангүй
              </button>
            </div>
          )}
          {phase === "done" && (
            <div className={`result ${outcome === "solved" ? "ok" : "bad"}`} style={{ marginTop: 18 }}>
              <p className="result-text">
                {outcome === "solved"
                  ? "Сайн байна! Одоо энэ сэдвээс хариу шалгадаг дасгал хийж бататгая."
                  : "Зүгээр — өөр жишээ үзэх эсвэл энэ сэдвийн хялбар дасгалаас эхэлье."}
              </p>
              <div className="actions" style={{ marginTop: 12 }}>
                {topic && (
                  <Link href={`/practice?topic=${encodeURIComponent(topic)}`} className="btn">
                    Энэ сэдвээс дасгал →
                  </Link>
                )}
                <button
                  className="btn light"
                  disabled={busy}
                  onClick={() => loadExample(own.text, own.topic, seen)}
                >
                  Өөр жишээ үзэх
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

export default function SimilarPage() {
  return (
    <Shell>
      <Suspense fallback={<Loading />}>
        <Similar />
      </Suspense>
    </Shell>
  );
}
