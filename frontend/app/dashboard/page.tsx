"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import Shell, { Loading } from "@/components/Shell";
import { api, getToken, MasteryItem, me, PlacementState, User } from "@/lib/api";

const pct = (x: number) => Math.round(x * 100);
const two = (n: number) => String(n).padStart(2, "0");

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [mastery, setMastery] = useState<MasteryItem[] | null>(null);
  const [placement, setPlacement] = useState<PlacementState | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    me()
      .then((u) => {
        setUser(u);
        if (u.role === "student") {
          api.get<MasteryItem[]>("/me/mastery").then(setMastery).catch((e) => setError(e.message));
          api.get<PlacementState>("/placement").then(setPlacement).catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

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

  return (
    <Shell>
      {!user && <Loading />}

      {user?.role === "student" && (
        <>
          {placement && placement.status !== "done" && (
            <div className="notice">
              <span>
                {placement.status === "active"
                  ? "Түвшин тогтоох тест дуусаагүй байна — үлдсэн хэдэн асуултаа хариулаарай."
                  : "Эхлээд 10 минутын түвшин тогтоох тест өгвөл дасгал яг танд тохирно."}
              </span>
              <Link href="/placement" className="btn small">
                {placement.status === "active" ? "Үргэлжлүүлэх →" : "Тест өгөх →"}
              </Link>
            </div>
          )}

          <div className="intro" style={{ maxWidth: 730 }}>
            <div className="eyebrow">Сайн уу, {firstName}</div>
            <h1 className="big">
              Ойлгох хүртлээ
              <br />
              хамтдаа бодъё.
            </h1>
            <p className="lead">
              Хариултыг шууд хэлэхийн оронд зөв асуултаар чиглүүлнэ. Өнөөдөр гацсан нэг бодлогоосоо
              эхэлж болно.
            </p>
          </div>

          <hr className="rule" />
          {error && <div className="error">{error}</div>}

          <div className="layout">
            <div>
              <div className="section-label">
                <h2>Өнөөдөр юунаас эхлэх вэ?</h2>
              </div>
              <div className="card practice">
                <span className="num">01 — ӨНӨӨДРИЙН ДАСГАЛ</span>
                <h3>Танд тохирох бодлогоос эхэлье.</h3>
                <p>
                  Систем таны эзэмшлийг харж, дараагийн алхамдаа хамгийн хэрэгтэй бодлогыг сонгоно.
                  Гацвал сануулга авч болно.
                </p>
                <div className="actions">
                  <Link href="/practice" className="btn rust">
                    Бодож эхлэх →
                  </Link>
                  <Link href="/upload" className="btn light">
                    Өөрийн бодлогоо оруулах
                  </Link>
                </div>
              </div>
            </div>

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
                  <span className="note-num">{two(i + 1)}</span>
                  <div>
                    <b>{m.name}</b>
                    <p>
                      {m.attempts_count === 0 ? "Шинэ сэдэв" : `Эзэмшил ${pct(m.p_mastery)}%`} · {m.grade}-р анги
                    </p>
                  </div>
                  <span className="arrow" aria-hidden>
                    ↗
                  </span>
                </Link>
              ))}
              {upNext.length > 0 && (
                <p className="tiny" style={{ marginTop: 22 }}>
                  Урьдач сэдвүүдээ эзэмшсэн, одоо сурахад бэлэн сэдвүүд.
                </p>
              )}
            </aside>
          </div>

          <hr className="rule" />

          {mastery && <Stats mastery={mastery} />}

          <div className="bottom" style={{ marginTop: 46 }}>
            <div>
              <div className="section-label">
                <h2>Бага багаар ахиц гаргана</h2>
              </div>
              <p className="muted" style={{ fontSize: 14, maxWidth: 440, lineHeight: 1.9 }}>
                Алдсан бодлого бүр ямар ойлголтоо давтах шаардлагатайг харуулна. Хурднаас илүү
                ойлголтоо чухалчилъя. Эзэмшил 95%-д хүрвэл сэдвийг эзэмшсэн гэж үзнэ.
              </p>
              <Link href="/placement" className="small-link">
                Түвшин тогтоох тест ↗
              </Link>
            </div>
            <div>
              <div className="section-label">
                <h2>Сэдвийн эзэмшил</h2>
                {mastery && <span className="muted">{mastery.length} сэдэв</span>}
              </div>
              {!mastery && <Loading />}
              <ul className="mastery-list">
                {mastery?.map((m) => (
                  <li key={m.topic_id}>
                    <Link
                      href={`/practice?topic=${encodeURIComponent(m.topic_id)}`}
                      className="mastery-row"
                      title="Энэ сэдвээс дасгал хийх"
                    >
                      <div className="mastery-name">
                        <span>{m.name}</span>
                        <span className="hint">
                          {m.grade}-р анги · {m.correct_count}/{m.attempts_count} зөв
                          {m.mastered ? " · эзэмшсэн ✓" : ""}
                        </span>
                      </div>
                      <div
                        className="bar"
                        role="progressbar"
                        aria-valuenow={pct(m.p_mastery)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${m.name} эзэмшил`}
                      >
                        <div className={`bar-fill ${m.mastered ? "done" : ""}`} style={{ width: `${pct(m.p_mastery)}%` }} />
                      </div>
                      <span className="mastery-pct">{pct(m.p_mastery)}%</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}

      {user?.role === "parent" && (
        <div className="page-head">
          <div className="eyebrow">Эцэг эхийн булан</div>
          <h1>Сайн уу, {firstName}</h1>
          <p>Хүүхдийнхээ ахиц, сул талыг энд харах боломж удахгүй нэмэгдэнэ.</p>
        </div>
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

function Stats({ mastery }: { mastery: MasteryItem[] }) {
  const attempts = mastery.reduce((s, m) => s + m.attempts_count, 0);
  const correct = mastery.reduce((s, m) => s + m.correct_count, 0);
  const mastered = mastery.filter((m) => m.mastered).length;
  return (
    <div className="stats">
      <div className="stat">
        <span className="large">{attempts}</span>
        <span className="caption">Нийт оролдлого</span>
      </div>
      <div className="stat">
        <span className="large">{correct}</span>
        <span className="caption">Зөв хариулт</span>
      </div>
      <div className="stat">
        <span className="large">
          {mastered}
          <span className="muted" style={{ fontFamily: "inherit", fontSize: 18 }}>
            {" "}
            / {mastery.length}
          </span>
        </span>
        <span className="caption">Эзэмшсэн сэдэв</span>
      </div>
    </div>
  );
}
