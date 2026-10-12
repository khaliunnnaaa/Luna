"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Shell, { Loading, PageHead } from "@/components/Shell";
import { api, getToken, MasteryItem } from "@/lib/api";

const pct = (x: number) => Math.round(x * 100);

// FR-12: ахицын самбар — зөвхөн ахицын мэдээлэл (тоо + сэдэв бүрийн эзэмшил).
export default function ProgressPage() {
  const [mastery, setMastery] = useState<MasteryItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    api.get<MasteryItem[]>("/me/mastery").then(setMastery).catch((e) => setError(e.message));
  }, []);

  const attempts = mastery?.reduce((s, m) => s + m.attempts_count, 0) ?? 0;
  const correct = mastery?.reduce((s, m) => s + m.correct_count, 0) ?? 0;
  const mastered = mastery?.filter((m) => m.mastered).length ?? 0;

  return (
    <Shell>
      <PageHead eyebrow="Миний ахиц" title="Чиний ахиц">
        Өөрийгөө бусадтай биш, өчигдрийн өөртэйгөө харьцуул. Эзэмшил 95%-д хүрвэл сэдвийг эзэмшсэн
        гэж үзнэ.
      </PageHead>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {!mastery && !error && <Loading />}

      {mastery && (
        <>
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

          <div className="section-label" style={{ marginTop: 46 }}>
            <h2>Сэдвийн эзэмшил</h2>
            <span className="muted">Сэдэв дээр дарж дасгал хийнэ</span>
          </div>
          {mastery.length === 0 && <p className="muted">Сэдэв бүртгэгдээгүй байна.</p>}
          <ul className="mastery-list">
            {mastery.map((m) => (
              <li key={m.topic_id}>
                <Link href={`/practice?topic=${encodeURIComponent(m.topic_id)}`} className="mastery-row">
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

          <p className="muted" style={{ marginTop: 30 }}>
            Эхлэх түвшин буруу санагдаж байвал{" "}
            <Link href="/placement" className="small-link">
              түвшин тогтоох тестээ дахин өг
            </Link>
          </p>
        </>
      )}
    </Shell>
  );
}
