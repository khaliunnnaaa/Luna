"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import ProblemSolver from "@/components/ProblemSolver";
import Shell, { Loading, PageHead } from "@/components/Shell";
import { api, getToken, NextProblem } from "@/lib/api";

// FR-09: системийн санал болгосон дараагийн дасгал. ?topic=T04 бол тухайн сэдвээс (FR-11).
function Practice() {
  const params = useSearchParams();
  const topic = params.get("topic");
  const [next, setNext] = useState<NextProblem | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    setNext(null);
    const q = topic ? `?topic_id=${encodeURIComponent(topic)}` : "";
    try {
      setNext(await api.get<NextProblem>(`/next${q}`));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError((e as Error).message);
    }
  }, [topic]);

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    load();
  }, [load]);

  return (
    <>
      <Link href="/dashboard" className="back">
        ← Нүүр рүү
      </Link>
      <PageHead
        eyebrow={topic && next?.problem ? `Дасгал · ${next.problem.topic_name}` : "Дасгал"}
        title="Нэг алхмаар эхэлье."
      >
        Хариуг яаралгүй, эхлээд яагаад гэдгийг нь бодоорой. Гацвал сануулга аваарай.
      </PageHead>

      {error && (
        <div className="error" role="alert">
          {error}{" "}
          <button type="button" className="link" onClick={load}>
            Дахин оролдох
          </button>
        </div>
      )}
      {!next && !error && <Loading label="Тохирох бодлого хайж байна..." />}
      {next && !next.problem && (
        <div className="card question">
          <p className="serif" style={{ fontSize: 22, margin: "0 0 18px" }}>
            {next.reason}
          </p>
          <div className="actions">
            <Link href="/dashboard" className="btn">
              Нүүр рүү буцах
            </Link>
            {topic && (
              <Link href="/practice" className="btn light">
                Өөр сэдвээс дасгал
              </Link>
            )}
          </div>
        </div>
      )}
      {next?.problem && <ProblemSolver problem={next.problem} reason={next.reason} onNext={load} />}
    </>
  );
}

export default function PracticePage() {
  return (
    <Shell>
      <Suspense fallback={<Loading />}>
        <Practice />
      </Suspense>
    </Shell>
  );
}
