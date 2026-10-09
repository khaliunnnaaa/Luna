"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import ProblemSolver from "@/components/ProblemSolver";
import { api, getToken, ProblemStudent } from "@/lib/api";

// Тодорхой нэг бодлогыг бодох (холбоосоор орж ирэх, түүхээс дахин бодох).
export default function ProblemPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [problem, setProblem] = useState<ProblemStudent | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .get<ProblemStudent>(`/problems/${id}`)
      .then(setProblem)
      .catch((e) => setError(e.message));
  }, [id, router]);

  return (
    <main className="student">
      <div className="student-top">
        <Link href="/dashboard" className="link">
          ← Самбар
        </Link>
        <h1>Бодлого {problem?.code ? `· ${problem.code}` : ""}</h1>
      </div>
      {error && <div className="error">{error}</div>}
      {problem && (
        <div className="card wide">
          <ProblemSolver problem={problem} onNext={() => router.push("/practice")} />
        </div>
      )}
    </main>
  );
}
