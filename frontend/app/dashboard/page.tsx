"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import Shell, { Loading } from "@/components/Shell";
import { api, getToken, MasteryItem, me, PlacementState, User } from "@/lib/api";

const pct = (x: number) => Math.round(x * 100);

// Нүүр = нэг асуулт: «Одоо юу хийх вэ?». Статистик, бүх сэдвийн эзэмшил → /progress.
export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [mastery, setMastery] = useState<MasteryItem[] | null>(null);
  const [placement, setPlacement] = useState<PlacementState | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    me()
      .then((u) => {
        if (u.role === "parent") {
          router.replace("/parent"); // эцэг эхийн нүүр — хүүхдийн ахиц (FR-14)
          return;
        }
        setUser(u);
        if (u.role === "student") {
          api.get<MasteryItem[]>("/me/mastery").then(setMastery).catch((e) => setError(e.message));
          api.get<PlacementState>("/placement").then(setPlacement).catch(() => {});
        }
      })
      .catch(() => {});
  }, [router]);

  // Дараа нь сурах сэдэв: эзэмшээгүй, урьдач сэдвүүд нь бүгд эзэмшигдсэн (recommender-тэй ижил санаа)
  const upNext = useMemo(() => {
    if (!mastery) return [];
    const done = new Set(mastery.filter((m) => m.mastered).map((m) => m.topic_id));
    return mastery
      .filter((m) => !m.mastered && m.prerequisites.every((p) => done.has(p)))
      .sort((a, b) => b.p_mastery - a.p_mastery)
      .slice(0, 3);
  }, [mastery]);

  const firstName = user?.full_name.trim().split(/\s+/).pop() ?? "";
  // Түвшин тогтоох тест өгөөгүй бол гол үйлдэл нь тест болно
  const needsPlacement = placement !== null && placement.status !== "done";

  return (
    <Shell>
      {!user && <Loading />}

      {user?.role === "student" && (
        <>
          <div className="page-head">
            <div className="eyebrow">Сайн уу, {firstName}</div>
            <h1>Өнөөдөр юунаас эхлэх вэ?</h1>
          </div>
          {error && <div className="error">{error}</div>}

          <div className="layout">
            {needsPlacement ? (
              <div className="card practice">
                <span className="num">Эхний алхам</span>
                <h3>Эхлээд түвшнээ тогтооё.</h3>
                <p>
                  {placement?.status === "active"
                    ? "Тест дуусаагүй байна — үлдсэн хэдэн асуултаа хариулаарай."
                    : "10 минутын богино тест. Шалгалт биш — дасгал яг танд тохирохын тулд."}
                </p>
                <div className="actions">
                  <Link href="/placement" className="btn rust">
                    {placement?.status === "active" ? "Тестээ үргэлжлүүлэх →" : "Тест эхлэх →"}
                  </Link>
                </div>
              </div>
            ) : (
              <div className="card practice">
                <span className="num">Өнөөдрийн дасгал</span>
                <h3>Танд тохирох бодлогоос эхэлье.</h3>
                <p>Систем таны эзэмшлийг харж, хамгийн хэрэгтэй бодлогыг сонгоно. Гацвал сануулга авна.</p>
                <div className="actions">
                  <Link href="/practice" className="btn rust">
                    Бодож эхлэх →
                  </Link>
                  <Link href="/upload" className="btn light">
                    Өөрийн бодлогоо оруулах
                  </Link>
                </div>
              </div>
            )}

            <aside>
              <div className="section-label">
                <h2>Үргэлжлүүлэн сурах</h2>
              </div>
              {!mastery && <Loading />}
              {mastery && upNext.length === 0 && (
                <p className="muted">
                  {mastery.length === 0
                    ? "Сэдэв бүртгэгдээгүй байна."
                    : "Бүх сэдвээ эзэмшсэн байна. Давтлага хийхэд дасгал руу ороорой."}
                </p>
              )}
              {upNext.map((m, i) => (
                <Link
                  key={m.topic_id}
                  href={`/practice?topic=${encodeURIComponent(m.topic_id)}`}
                  className="note-line"
                >
                  <span className="note-num">{i + 1}</span>
                  <div>
                    <b>{m.name}</b>
                    <p>{m.attempts_count === 0 ? "Шинэ сэдэв" : `Эзэмшил ${pct(m.p_mastery)}%`}</p>
                  </div>
                  <span className="arrow" aria-hidden>
                    ↗
                  </span>
                </Link>
              ))}
              {mastery && mastery.length > 0 && (
                <Link href="/progress" className="small-link" style={{ marginTop: 22 }}>
                  Бүх сэдэв, ахицаа харах ↗
                </Link>
              )}
            </aside>
          </div>
        </>
      )}

      {user?.role === "admin" && (
        <div className="page-head">
          <div className="eyebrow">Админ</div>
          <h1>Контент удирдлага</h1>
          <p>Бодлого, сэдэв, нэр томьёог засварлана.</p>
          <span style={{ display: "block", marginTop: 22 }}>
            <Link href="/admin/problems" className="btn rust">
              Удирдлага руу →
            </Link>
          </span>
        </div>
      )}
    </Shell>
  );
}
