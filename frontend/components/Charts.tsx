"use client";

import { useEffect, useRef, useState } from "react";

// FR-14 эцэг эхийн тайлангийн графикууд — гадны сангүй SVG.
// Dataviz дүрэм: нимгэн тэмдэглэгээ (багана ≤24px, 4px дугуй орой), сегмент хооронд 2px зай,
// 2+ цуваа бол legend, hover/focus tooltip, хүснэгт хэлбэрээр харах боломж, текст өнгөгүй.
// Палитр (validate_palette.js — 6 шалгуур PASS, цагаан дэвсгэр дээр):
export const C_CORRECT = "#1f8159";
export const C_WRONG = "#c4812f";
const GRID = "#ebe9e2";
const AXIS = "#63665e";

const WEEKDAY = ["Ням", "Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан", "Бямба"];
const parse = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const shortDate = (iso: string) => {
  const d = parse(iso);
  return `${d.getMonth() + 1}.${d.getDate()}`;
};
export const longDate = (iso: string) => {
  const d = parse(iso);
  return `${d.getMonth() + 1}-р сарын ${d.getDate()}, ${WEEKDAY[d.getDay()]}`;
};

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

// Зөвхөн дээд талдаа 4px дугуйлсан тэгш өнцөгт (суурь нь шулуун)
function topRounded(x: number, y: number, w: number, h: number, r = 4) {
  const rr = Math.min(r, h, w / 2);
  return `M${x},${y + h} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + w - rr} Q${x + w},${y} ${x + w},${y + rr} V${y + h} Z`;
}

function niceMax(v: number) {
  if (v <= 4) return 4;
  const step = v <= 10 ? 2 : v <= 20 ? 5 : 10;
  return Math.ceil(v / step) * step;
}

type Tip = { x: number; y: number; title: string; rows: { color: string; label: string; value: string }[] };

function Tooltip({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  return (
    <div className="chart-tip" style={{ left: tip.x, top: tip.y }} role="status">
      <div className="chart-tip-title">{tip.title}</div>
      {tip.rows.map((r) => (
        <div key={r.label} className="chart-tip-row">
          <span className="key-line" style={{ background: r.color }} />
          <strong>{r.value}</strong>
          <span>{r.label}</span>
        </div>
      ))}
    </div>
  );
}

// ---------- 1. Өдөр бүрийн идэвх: зөв/буруу давхарласан багана ----------
export function ActivityChart({ data }: { data: { date: string; correct: number; wrong: number }[] }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const H = 200;
  const pad = { l: 28, r: 8, t: 10, b: 26 };
  const iw = width - pad.l - pad.r;
  const ih = H - pad.t - pad.b;
  const max = niceMax(Math.max(...data.map((d) => d.correct + d.wrong), 0));
  const band = iw / data.length;
  const bw = Math.min(24, band * 0.62);
  const y = (v: number) => pad.t + ih - (v / max) * ih;
  const ticks = [0, max / 2, max];
  const empty = data.every((d) => d.correct + d.wrong === 0);

  const show = (i: number) => {
    const d = data[i];
    setActive(i);
    setTip({
      x: pad.l + band * i + band / 2,
      y: y(d.correct + d.wrong) - 8,
      title: longDate(d.date),
      rows: [
        { color: C_CORRECT, label: "зөв", value: String(d.correct) },
        { color: C_WRONG, label: "буруу", value: String(d.wrong) },
      ],
    });
  };
  const hide = () => {
    setActive(null);
    setTip(null);
  };

  return (
    <figure className="chart">
      <div className="chart-legend" aria-hidden>
        <span><i style={{ background: C_CORRECT }} />Зөв</span>
        <span><i style={{ background: C_WRONG }} />Буруу</span>
      </div>
      <div ref={ref} className="chart-area" onPointerLeave={hide}>
        <svg width={width} height={H} role="img" aria-label="Сүүлийн 14 өдөр бодсон бодлого, зөв ба буруугаар">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} />
              <text x={pad.l - 8} y={y(t)} dy="0.35em" textAnchor="end" className="chart-axis">
                {t}
              </text>
            </g>
          ))}
          {data.map((d, i) => {
            const cx = pad.l + band * i + band / 2;
            const x = cx - bw / 2;
            const hc = (d.correct / max) * ih;
            const hw = (d.wrong / max) * ih;
            const gap = d.correct && d.wrong ? 2 : 0;
            const base = pad.t + ih;
            const dim = active !== null && active !== i ? 0.45 : 1;
            return (
              <g key={d.date} opacity={dim}>
                {d.correct > 0 && (
                  d.wrong > 0
                    ? <rect x={x} y={base - hc} width={bw} height={hc} fill={C_CORRECT} />
                    : <path d={topRounded(x, base - hc, bw, hc)} fill={C_CORRECT} />
                )}
                {d.wrong > 0 && (
                  <path d={topRounded(x, base - hc - gap - hw, bw, hw)} fill={C_WRONG} />
                )}
                {(i % 2 === data.length % 2 || i === data.length - 1) && (
                  <text x={cx} y={H - 8} textAnchor="middle" className="chart-axis">
                    {i === data.length - 1 ? "Өнөөдөр" : shortDate(d.date)}
                  </text>
                )}
                {/* Hit target — баганаас том (бүтэн зурвас) */}
                <rect
                  x={pad.l + band * i}
                  y={pad.t}
                  width={band}
                  height={ih}
                  fill="transparent"
                  tabIndex={0}
                  aria-label={`${longDate(d.date)}: ${d.correct} зөв, ${d.wrong} буруу`}
                  onPointerMove={() => show(i)}
                  onFocus={() => show(i)}
                  onBlur={hide}
                />
              </g>
            );
          })}
          <line x1={pad.l} x2={width - pad.r} y1={pad.t + ih} y2={pad.t + ih} stroke="#d9d8cf" />
        </svg>
        {empty && <div className="chart-empty">Сүүлийн 14 өдөр бодлого бодоогүй байна</div>}
        <Tooltip tip={tip} />
      </div>
      <DataTable
        head={["Өдөр", "Зөв", "Буруу"]}
        rows={data.map((d) => [longDate(d.date), d.correct, d.wrong])}
      />
    </figure>
  );
}

// ---------- 2. Дундаж эзэмшлийн өөрчлөлт: шугам + бүдэг талбай ----------
export function TrendChart({ data }: { data: { date: string; avg_mastery: number }[] }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const H = 200;
  const pad = { l: 40, r: 44, t: 12, b: 26 };
  const iw = width - pad.l - pad.r;
  const ih = H - pad.t - pad.b;
  const x = (i: number) => pad.l + (i / Math.max(1, data.length - 1)) * iw;
  const y = (v: number) => pad.t + ih - v * ih;
  const pts = data.map((d, i) => [x(i), y(d.avg_mastery)] as const);
  const line = pts.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join(" ");
  const area = `${line} L${x(data.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
  const last = data[data.length - 1];
  const first = data[0];
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
    const i = Math.round(((e.clientX - box.left - pad.l) / iw) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, i)));
  };
  const h = hover !== null ? data[hover] : null;

  return (
    <figure className="chart">
      <div ref={ref} className="chart-area" onPointerLeave={() => setHover(null)}>
        <svg width={width} height={H} role="img" aria-label={`Сүүлийн 30 өдрийн дундаж эзэмшил: ${pct(first.avg_mastery)}-аас ${pct(last.avg_mastery)}`}>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <g key={t}>
              <line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} />
              <text x={pad.l - 8} y={y(t)} dy="0.35em" textAnchor="end" className="chart-axis">
                {pct(t)}
              </text>
            </g>
          ))}
          <path d={area} fill={C_CORRECT} opacity={0.1} />
          <path d={line} fill="none" stroke={C_CORRECT} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {[0, Math.floor((data.length - 1) / 2), data.length - 1].map((i) => (
            <text key={i} x={x(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === data.length - 1 ? "end" : "middle"} className="chart-axis">
              {i === data.length - 1 ? "Өнөөдөр" : shortDate(data[i].date)}
            </text>
          ))}
          {/* Төгсгөлийн утгыг шууд шошголно */}
          <circle cx={x(data.length - 1)} cy={y(last.avg_mastery)} r={5} fill={C_CORRECT} stroke="#fff" strokeWidth={2} />
          <text x={x(data.length - 1) + 9} y={y(last.avg_mastery)} dy="0.35em" className="chart-value">
            {pct(last.avg_mastery)}
          </text>
          {h && hover !== null && (
            <g pointerEvents="none">
              <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={pad.t + ih} stroke="#cfcfc6" />
              <circle cx={x(hover)} cy={y(h.avg_mastery)} r={5} fill={C_CORRECT} stroke="#fff" strokeWidth={2} />
            </g>
          )}
          <rect
            x={pad.l}
            y={pad.t}
            width={iw}
            height={ih}
            fill="transparent"
            tabIndex={0}
            aria-label="Өдөр сонгохын тулд сум товч ашиглана уу"
            onPointerMove={onMove}
            onFocus={() => setHover(data.length - 1)}
            onBlur={() => setHover(null)}
            onKeyDown={(e) => {
              if (e.key === "ArrowLeft") setHover((v) => Math.max(0, (v ?? data.length - 1) - 1));
              if (e.key === "ArrowRight") setHover((v) => Math.min(data.length - 1, (v ?? 0) + 1));
            }}
          />
        </svg>
        {h && hover !== null && (
          <Tooltip
            tip={{
              x: x(hover),
              y: y(h.avg_mastery) - 10,
              title: longDate(h.date),
              rows: [{ color: C_CORRECT, label: "дундаж эзэмшил", value: pct(h.avg_mastery) }],
            }}
          />
        )}
      </div>
      <DataTable
        head={["Өдөр", "Дундаж эзэмшил"]}
        rows={data.map((d) => [longDate(d.date), pct(d.avg_mastery)])}
      />
    </figure>
  );
}

// ---------- 3. Сэдэв бүрийн эзэмшил: хэвтээ багана + 95% зорилтын тэмдэг ----------
export function MasteryBars({
  items,
}: {
  items: { topic_id: string; name: string; p_mastery: number; mastered: boolean; attempts_count: number }[];
}) {
  return (
    <figure className="chart">
      <ul className="mbars">
        {items.map((m) => {
          const p = Math.round(m.p_mastery * 100);
          return (
            <li key={m.topic_id} className="mbar">
              <span className="mbar-name">
                {m.name}
                {m.attempts_count === 0 && <small> · эхлээгүй</small>}
              </span>
              <span
                className="mbar-track"
                role="progressbar"
                aria-valuenow={p}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${m.name}: ${p}%${m.mastered ? ", эзэмшсэн" : ""}`}
              >
                <span
                  className="mbar-fill"
                  style={{ width: `${p}%`, background: m.mastered ? C_CORRECT : "#8fb3a1" }}
                />
                <span className="mbar-target" title="Эзэмшсэн гэж тооцох хэмжээ: 95%" />
              </span>
              <span className="mbar-pct">
                {p}%{m.mastered && <span className="mbar-ok"> ✓</span>}
              </span>
            </li>
          );
        })}
      </ul>
      <figcaption className="tiny">
        Босоо зураас — 95%: энэ хэмжээнд хүрвэл сэдвийг эзэмшсэн гэж тооцно. Тод ногоон — эзэмшсэн.
      </figcaption>
    </figure>
  );
}

function DataTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <details className="chart-table">
      <summary>Хүснэгтээр харах</summary>
      <table>
        <thead>
          <tr>{head.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
