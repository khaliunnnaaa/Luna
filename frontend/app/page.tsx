"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import MathText from "@/components/MathText";
import { Footer } from "@/components/Shell";
import { getToken } from "@/lib/api";

export default function Home() {
  // Нэвтэрсэн хэрэглэгчид "Самбар руу" товч харуулна
  const [authed, setAuthed] = useState(false);
  useEffect(() => setAuthed(!!getToken()), []);

  return (
    <div className="site">
      <header className="top">
        <Link href="/" className="logo">
          алхам
        </Link>
        <div className="account">
          {authed ? (
            <Link href="/dashboard" className="btn small rust">
              Самбар руу →
            </Link>
          ) : (
            <>
              <Link href="/login" className="logout" style={{ fontSize: 13, fontWeight: 600, textDecoration: "none" }}>
                Нэвтрэх
              </Link>
              <Link href="/register" className="btn small rust">
                Бүртгүүлэх
              </Link>
            </>
          )}
        </div>
      </header>

      <main className="wrap" id="main">
        <section className="landing-hero">
          <div>
            <div className="eyebrow">Математикийн туслах</div>
            <h1 className="big">
              Ойлгох хүртлээ
              <br />
              хамтдаа бодъё.
            </h1>
            <p className="lead">
              Хариултыг шууд хэлэхийн оронд зөв асуулт, шатлан сануулгаар чиглүүлнэ. Гацсан нэг
              бодлогоосоо эхэлж болно.
            </p>
            <div className="actions" style={{ marginTop: 30 }}>
              <Link href={authed ? "/dashboard" : "/register"} className="btn rust">
                {authed ? "Үргэлжлүүлэх →" : "Үнэгүй эхлэх →"}
              </Link>
              {!authed && (
                <Link href="/login" className="btn light">
                  Бүртгэлтэй юу? Нэвтрэх
                </Link>
              )}
            </div>
          </div>

          <div className="card landing-card" aria-hidden>
            <div className="indexline">
              <span>Алхам 01 / 03</span>
              <span>Квадрат тэгшитгэл</span>
            </div>
            <div className="math">
              <MathText text="$x^2 - 5x + 6 = 0$" />
            </div>
            <p className="serif" style={{ fontSize: 19, lineHeight: 1.4, margin: "0 0 14px" }}>
              Үржвэр нь 6, нийлбэр нь −5 байх хоёр тоо аль вэ?
            </p>
            <ol className="hints">
              <li>Үржвэр эерэг, нийлбэр сөрөг — хоёр тоо ямар тэмдэгтэй байх вэ?</li>
            </ol>
          </div>
        </section>

        <hr className="rule" />

        <section className="how">
          <div>
            <span className="note-num">01</span>
            <h3>Түвшнээ тогтоо</h3>
            <p>10 минутын богино тестээр хаанаас эхлэхээ мэднэ. Энэ нь шалгалт биш.</p>
          </div>
          <div>
            <span className="note-num">02</span>
            <h3>Алхам алхмаар бод</h3>
            <p>Гацвал шатлан сануулга авна. Ойлгохгүй үг дээр дарвал тайлбар гарна.</p>
          </div>
          <div>
            <span className="note-num">03</span>
            <h3>Ахицаа хар</h3>
            <p>Бодсон бодлого бүр сэдвийн эзэмшилд нөлөөлж, дараагийн дасгалыг тохируулна.</p>
          </div>
        </section>

      </main>
      <Footer />
    </div>
  );
}
