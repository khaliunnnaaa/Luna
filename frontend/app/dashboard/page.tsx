"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, getToken, logout, MasteryItem, me, PlacementState, ROLE_LABEL, User } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [mastery, setMastery] = useState<MasteryItem[]>([]);
  const [placement, setPlacement] = useState<PlacementState | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    me()
      .then((u) => {
        setUser(u);
        if (u.role === "student") {
          api.get<MasteryItem[]>("/me/mastery").then(setMastery).catch((e) => setError(e.message));
          api.get<PlacementState>("/placement").then(setPlacement).catch(() => {});
        }
      })
      .catch(() => {
        logout();
        router.replace("/login");
      });
  }, [router]);

  function onLogout() {
    logout();
    router.push("/");
  }

  if (!user) {
    return (
      <main className="page">
        <p className="subtitle">Ачаалж байна...</p>
      </main>
    );
  }

  const total = mastery.reduce((s, m) => s + m.attempts_count, 0);
  const solvedTopics = mastery.filter((m) => m.mastered).length;
  const pct = (x: number) => Math.round(x * 100);

  return (
    <main className="student">
      <div className="student-top">
        <div>
          <span className="badge">{ROLE_LABEL[user.role]}</span>
          <h1 style={{ marginTop: 8 }}>Сайн уу, {user.full_name}!</h1>
        </div>
        <button className="btn secondary small" onClick={onLogout}>
          Гарах
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {user.role === "student" && (
        <>
          {placement && placement.status !== "done" && (
            <div className="notice">
              <span>
                {placement.status === "active"
                  ? "Түвшин тогтоох тест дуусаагүй байна."
                  : "Эхлээд 10 минутын түвшин тогтоох тест өгвөл дасгал яг танд тохирно."}
              </span>
              <Link href="/placement" className="btn">
                {placement.status === "active" ? "Үргэлжлүүлэх" : "Тест өгөх"}
              </Link>
            </div>
          )}
          <div className="card wide cta">
            <div>
              <h2>Өнөөдрийн дасгал</h2>
              <p className="subtitle" style={{ marginBottom: 0 }}>
                Систем таны мэдэхгүй байгаа ойлголтоос эхлэн тохирох бодлого санал болгоно.
              </p>
            </div>
            <div className="stack" style={{ minWidth: 200 }}>
              <Link href="/practice" className="btn">
                Бодож эхлэх →
              </Link>
              <Link href="/upload" className="btn secondary">
                📷 Бодлогын зураг оруулах
              </Link>
            </div>
          </div>

          <div className="stats">
            <div className="stat">
              <span className="stat-num">{total}</span>
              <span className="hint">оролдлого</span>
            </div>
            <div className="stat">
              <span className="stat-num">{solvedTopics}</span>
              <span className="hint">эзэмшсэн сэдэв</span>
            </div>
            <div className="stat">
              <span className="stat-num">{mastery.length}</span>
              <span className="hint">нийт сэдэв</span>
            </div>
          </div>

          <div className="card wide">
            <h2>Сэдвийн эзэмшил</h2>
            <p className="hint">Сэдэв дээр дарвал тэр сэдвээс дасгал өгнө. 95%-иас дээш бол эзэмшсэн гэж үзнэ.</p>
            {mastery.length === 0 && <p className="subtitle">Сэдэв бүртгэгдээгүй байна.</p>}
            <ul className="mastery-list">
              {mastery.map((m) => (
                <li key={m.topic_id}>
                  <Link href={`/practice?topic=${encodeURIComponent(m.topic_id)}`} className="mastery-row">
                    <div className="mastery-name">
                      <span>{m.name}</span>
                      <span className="hint">
                        {m.grade}-р анги · {m.correct_count}/{m.attempts_count} зөв
                        {m.mastered ? " · ✓" : ""}
                      </span>
                    </div>
                    <div className="bar">
                      <div
                        className={`bar-fill ${m.mastered ? "done" : ""}`}
                        style={{ width: `${pct(m.p_mastery)}%` }}
                      />
                    </div>
                    <span className="mastery-pct">{pct(m.p_mastery)}%</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {user.role === "parent" && (
        <div className="card wide">
          <p>Эцэг эхийн самбар удахгүй: хүүхдийнхээ ахиц, сул талыг энд харна.</p>
        </div>
      )}

      {user.role === "admin" && (
        <div className="card wide">
          <Link href="/admin" className="btn">
            Контент удирдлага
          </Link>
        </div>
      )}
    </main>
  );
}
