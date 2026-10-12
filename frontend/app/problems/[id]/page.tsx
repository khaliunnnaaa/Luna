"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import ProblemSolver from "@/components/ProblemSolver";
import Shell, { Loading, PageHead } from "@/components/Shell";
import { api, getToken, ProblemStudent } from "@/lib/api";

// Тодорхой нэг бодлогыг бодох (холбоосоор орж ирэх, түүхээс дахин бодох).
export default function ProblemPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [problem, setProblem] = useState<ProblemStudent | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    api
      .get<ProblemStudent>(`/problems/${id}`)
      .then(setProblem)
      .catch((e) => setError(e.message));
  }, [id]);

  return (
    <Shell>
      <Link href="/dashboard" className="back">
        ← Нүүр рүү
      </Link>
      <PageHead eyebrow={problem ? `Бодлого / ${problem.topic_name}` : "Бодлого"} title="Хамтдаа бодъё." />
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {!problem && !error && <Loading />}
      {problem && <ProblemSolver problem={problem} onNext={() => router.push("/practice")} />}
    </Shell>
  );
}
