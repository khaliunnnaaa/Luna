"use client";

import { useEffect, useState } from "react";

import { api, LinkCode, Person } from "@/lib/api";

// FR-14 (сурагчийн тал): эцэг эхэд өгөх код үүсгэх, хэн харж байгааг харах, холбоог салгах.
export default function ParentLink() {
  const [parents, setParents] = useState<Person[] | null>(null);
  const [code, setCode] = useState<LinkCode | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    api.get<Person[]>("/me/parents").then(setParents).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function create() {
    setError("");
    setBusy(true);
    try {
      setCode(await api.post<LinkCode>("/me/link-code", {}));
      setCopied(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(p: Person) {
    if (!confirm(`${p.full_name} таны ахицыг харахаа болих уу?`)) return;
    try {
      await api.del(`/me/parents/${p.id}`);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function copy() {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code.code);
      setCopied(true);
    } catch {
      /* clipboard хаалттай бол код дэлгэцэн дээр харагдсаар байна */
    }
  }

  const expires = code
    ? new Date(code.expires_at).toLocaleString("mn-MN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <section className="card" style={{ marginTop: 36 }}>
      <div className="section-label">
        <h2>Эцэг эхтэй холбох</h2>
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        Эцэг эх тань энэ кодоор холбогдож, таны ахицыг харж, хамт суралцах зөвлөмж авна.
      </p>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {code ? (
        <div className="code-box">
          <span className="code-value" aria-label={`Холбох код ${code.code.split("").join(" ")}`}>
            {code.code}
          </span>
          <div>
            <button type="button" className="btn small light" onClick={copy}>
              {copied ? "Хуулсан ✓" : "Хуулах"}
            </button>
            <p className="tiny" style={{ margin: "6px 0 0" }}>
              {expires} хүртэл хүчинтэй, нэг удаа ашиглагдана.
            </p>
          </div>
        </div>
      ) : (
        <button type="button" className="btn" onClick={create} disabled={busy}>
          {busy ? "Үүсгэж байна..." : "Код үүсгэх"}
        </button>
      )}

      {parents && parents.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <p className="hint" style={{ margin: "0 0 8px" }}>
            Таны ахицыг харж байгаа:
          </p>
          <ul className="list">
            {parents.map((p) => (
              <li key={p.id} className="item" style={{ alignItems: "center" }}>
                <span className="item-main">{p.full_name}</span>
                <button type="button" className="btn small danger" onClick={() => remove(p)}>
                  Салгах
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
