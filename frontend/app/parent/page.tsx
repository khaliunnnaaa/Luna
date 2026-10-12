"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { ActivityChart, MasteryBars, TrendChart } from "@/components/Charts";
import Shell, { Loading, PageHead } from "@/components/Shell";
import { api, getToken, ParentReport, Person } from "@/lib/api";

// FR-14: эцэг эхийн самбар — хүүхэдтэй холбогдох, ахицыг графикаар харах, хамт хийх зөвлөмж.
export default function ParentPage() {
  const [children, setChildren] = useState<Person[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [report, setReport] = useState<ParentReport | null>(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  const loadChildren = useCallback(async (pick?: number) => {
    try {
      const list = await api.get<Person[]>("/parent/children");
      setChildren(list);
      setSelected((cur) => pick ?? cur ?? list[0]?.id ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    loadChildren();
  }, [loadChildren]);

  useEffect(() => {
    if (selected === null) return;
    setReport(null);
    api
      .get<ParentReport>(`/parent/children/${selected}/report`)
      .then(setReport)
      .catch((e) => setError(e.message));
  }, [selected]);

  async function unlink(id: number, name: string) {
    if (!confirm(`${name}-тэй холбоог салгах уу? Дахин холбоход шинэ код хэрэгтэй.`)) return;
    try {
      await api.del(`/parent/children/${id}`);
      setSelected(null);
      setReport(null);
      loadChildren();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const hasChildren = children !== null && children.length > 0;

  return (
    <Shell>
      <PageHead eyebrow="Эцэг эхийн булан" title="Хүүхдийн ахиц">
        Хүүхэд тань юу сурч, хаана гацаж байгааг харж, хамтдаа хэрхэн дэмжих зөвлөмж авна.
      </PageHead>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {children === null && !error && <Loading />}

      {children !== null && (!hasChildren || adding) && (
        <LinkChild
          first={!hasChildren}
          onCancel={hasChildren ? () => setAdding(false) : undefined}
          onLinked={(c) => {
            setAdding(false);
            loadChildren(c.id);
          }}
        />
      )}

      {hasChildren && !adding && (
        <>
          <div className="child-tabs" role="tablist" aria-label="Хүүхэд сонгох">
            {children.map((c) => (
              <button
                key={c.id}
                role="tab"
                aria-selected={selected === c.id}
                className={`child-tab ${selected === c.id ? "on" : ""}`}
                onClick={() => setSelected(c.id)}
              >
                <span className="portrait small" aria-hidden>
                  {c.full_name.trim().charAt(0).toUpperCase()}
                </span>
                {c.full_name}
              </button>
            ))}
            <button className="child-tab add" onClick={() => setAdding(true)}>
              + Хүүхэд нэмэх
            </button>
          </div>

          {!report && <Loading label="Тайлан бэлдэж байна..." />}
          {report && <Report report={report} onUnlink={() => unlink(report.child.id, report.child.full_name)} />}
        </>
      )}
    </Shell>
  );
}

function LinkChild({
  first,
  onLinked,
  onCancel,
}: {
  first: boolean;
  onLinked: (c: Person) => void;
  onCancel?: () => void;
}) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      onLinked(await api.post<Person>("/parent/children", { code: code.trim().toUpperCase() }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="layout">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{first ? "Хүүхэдтэйгээ холбогдох" : "Өөр хүүхэд нэмэх"}</h2>
        <ol className="steps" style={{ margin: "14px 0 22px" }}>
          <li className="step">Хүүхэд тань өөрийн бүртгэлээр нэвтэрч, «Миний ахиц» хуудас руу орно.</li>
          <li className="step">«Эцэг эхтэй холбох» хэсгээс 6 тэмдэгттэй код үүсгэнэ.</li>
          <li className="step">Тэр кодыг доор оруулна. Код 48 цаг хүчинтэй, нэг удаа ашиглагдана.</li>
        </ol>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="code">Холбох код</label>
            <input
              id="code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="жишээ: K7M2QX"
              maxLength={12}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              className="code-input"
              autoFocus
            />
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <div className="actions">
            <button className="btn rust" disabled={busy || code.trim().length < 4}>
              {busy ? "Холбож байна..." : "Холбох →"}
            </button>
            {onCancel && (
              <button type="button" className="btn light" onClick={onCancel}>
                Болих
              </button>
            )}
          </div>
        </form>
      </div>
      <aside className="reason" style={{ alignSelf: "start" }}>
        <strong>Яагаад код хэрэгтэй вэ?</strong>
        <p style={{ margin: "6px 0 0" }}>
          Хүүхдийн мэдээллийг зөвхөн түүний зөвшөөрлөөр харна. Хүүхэд тань хэн өөрийг нь харж байгааг
          мэдэх бөгөөд хүссэн үедээ холбоог салгаж болно.
        </p>
      </aside>
    </div>
  );
}

function lastActive(days: number | null) {
  if (days === null) return "Одоохондоо идэвхгүй";
  if (days === 0) return "Өнөөдөр идэвхтэй байсан";
  if (days === 1) return "Өчигдөр идэвхтэй байсан";
  return `${days} өдрийн өмнө идэвхтэй байсан`;
}

function Report({ report, onUnlink }: { report: ParentReport; onUnlink: () => void }) {
  const s = report.summary;
  const first = report.trend[0]?.avg_mastery ?? 0;
  const last = report.trend[report.trend.length - 1]?.avg_mastery ?? 0;
  const change = Math.round((last - first) * 100);

  return (
    <div className="report">
      <p className="muted" style={{ margin: "0 0 18px" }}>
        {lastActive(s.days_since_active)}
        {!s.placement_done && " · түвшин тогтоох тест өгөөгүй"}
      </p>

      <div className="stats four">
        <div className="stat">
          <span className="large">
            {s.topics_mastered}
            <small> / {s.topics_total}</small>
          </span>
          <span className="caption">Эзэмшсэн сэдэв</span>
        </div>
        <div className="stat">
          <span className="large">{s.attempts_7d}</span>
          <span className="caption">Энэ 7 хоногт бодсон</span>
        </div>
        <div className="stat">
          <span className="large">{s.accuracy_7d === null ? "—" : `${Math.round(s.accuracy_7d * 100)}%`}</span>
          <span className="caption">Зөв хариулт (7 хоног)</span>
        </div>
        <div className="stat">
          <span className="large">
            {s.active_days_14}
            <small> / 14</small>
          </span>
          <span className="caption">Идэвхтэй өдөр</span>
        </div>
      </div>

      {report.tips.length > 0 && (
        <section className="report-section">
          <div className="section-label">
            <h2>Хамтдаа юу хийх вэ?</h2>
          </div>
          <div className="tips">
            {report.tips.map((t, i) => (
              <div key={i} className={`tip-card ${t.kind}`}>
                <strong>{t.title}</strong>
                <p>{t.text}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="bottom report-section">
        <section className="card">
          <div className="section-label">
            <h2>Өдөр бүрийн идэвх</h2>
            <span className="muted">сүүлийн 14 өдөр</span>
          </div>
          <ActivityChart data={report.activity} />
        </section>
        <section className="card">
          <div className="section-label">
            <h2>Дундаж эзэмшил</h2>
            <span className="muted">
              30 өдөрт {change >= 0 ? "+" : ""}
              {change}%
            </span>
          </div>
          <TrendChart data={report.trend} />
        </section>
      </div>

      <section className="card report-section">
        <div className="section-label">
          <h2>Сэдэв бүрийн эзэмшил</h2>
        </div>
        <MasteryBars items={report.mastery} />
      </section>

      {(report.errors.length > 0 || report.hints_avg !== null) && (
        <section className="card report-section">
          <div className="section-label">
            <h2>Алдааны төрөл</h2>
            <span className="muted">сүүлийн 30 өдөр</span>
          </div>
          {report.errors.length === 0 ? (
            <p className="muted">Алдаа гараагүй байна.</p>
          ) : (
            <ul className="mbars">
              {report.errors.map((e) => {
                const max = report.errors[0].count;
                return (
                  <li key={e.type} className="mbar">
                    <span className="mbar-name">{e.label}</span>
                    <span className="mbar-track">
                      <span className="mbar-fill" style={{ width: `${(e.count / max) * 100}%`, background: "#c4812f" }} />
                    </span>
                    <span className="mbar-pct">{e.count}</span>
                  </li>
                );
              })}
            </ul>
          )}
          {report.hints_avg !== null && (
            <p className="tiny" style={{ marginBottom: 0 }}>
              Нэг бодлогод дунджаар {report.hints_avg} сануулга ашигласан (3-аас).
            </p>
          )}
        </section>
      )}

      <p className="tiny report-section">
        Тоонууд нь хүүхдийн системд бодсон бодлогоос бодит цагаар тооцогдоно.{" "}
        <button type="button" className="link" style={{ fontSize: 13 }} onClick={onUnlink}>
          Холбоог салгах
        </button>
      </p>
    </div>
  );
}
