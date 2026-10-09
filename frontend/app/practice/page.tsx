"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import ProblemSolver from "@/components/ProblemSolver";
import { api, getToken, NextProblem } from "@/lib/api";

// FR-09: системийн санал болгосон дараагийн дасгал. ?topic=T04 бол тухайн сэдвээс (FR-11).
function Practice() {
  const router = useRouter();
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
    } catch (e) {
      setError((e as Error).message);
    }
  }, [topic]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [load, router]);

  return (
    <main className="student">
      <div className="student-top">
        <Link href="/dashboard" className="link">
          ← Самбар
        </Link>
        <h1>Дасгал</h1>
      </div>
      {error && <div className="error">{error}</div>}
      {!next && !error && <p className="subtitle">Тохирох бодлого хайж байна...</p>}
      {next && !next.problem && (
        <div className="card wide">
          <p>{next.reason}</p>
          <Link href="/dashboard" className="btn secondary">
            Самбар руу буцах
          </Link>
        </div>
      )}
      {next?.problem && (
        <div className="card wide">
          <ProblemSolver problem={next.problem} reason={next.reason} onNext={load} />
        </div>
      )}
    </main>
  );
}

export default function PracticePage() {
  return (
    <Suspense fallback={<main className="student" />}>
      <Practice />
    </Suspense>
  );
}
