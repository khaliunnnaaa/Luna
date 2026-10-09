"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChangeEvent, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import {
  api,
  ClassifyResult,
  DIFFICULTY_LABEL,
  getToken,
  MlHealth,
  Topic,
  UploadDetail,
  uploadImage,
} from "@/lib/api";

// FR-03: зураг (камер/файл) → OCR → засах; FR-04: сэдэв ангилах; NFR-07: ML-гүй бол гараар бичих.
export default function UploadPage() {
  const router = useRouter();
  const [health, setHealth] = useState<MlHealth | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadDetail | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<ClassifyResult | null>(null);
  const [chosenTopic, setChosenTopic] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api.get<MlHealth>("/ml/health").then(setHealth).catch(() => setHealth({ available: false, classifier: false, ocr: false }));
    api.get<Topic[]>("/topics").then(setTopics).catch(() => {});
  }, [router]);

  async function onFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setResult(null);
    setPreview(URL.createObjectURL(file));
    setBusy("Зургийг таньж байна...");
    try {
      const u = await uploadImage(file);
      setUpload(u);
      setText(u.edited_text ?? "");
      if (u.predicted_topic) {
        setChosenTopic(u.predicted_topic);
        setResult({
          available: true,
          topic_id: u.predicted_topic,
          topic_name: u.topic_name,
          difficulty: null,
          confidence: null,
          subtopics: [],
          terms: [],
        });
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function classify() {
    if (!text.trim()) return;
    setError("");
    setBusy("Сэдвийг тодорхойлж байна...");
    try {
      if (upload) {
        const u = await api.put<UploadDetail>(`/uploads/${upload.id}`, { edited_text: text });
        setUpload(u);
      }
      const r = await api.post<ClassifyResult>("/classify", { text });
      setResult(r);
      if (r.topic_id) setChosenTopic(r.topic_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function removeImage() {
    if (!upload) return;
    try {
      await api.del(`/uploads/${upload.id}`);
    } catch (err) {
      setError((err as Error).message);
      return;
    }
    setUpload(null);
    setPreview(null);
    setText("");
    setResult(null);
  }

  const ocrOff = health !== null && !(health.available && health.ocr);
  const clfOff = health !== null && !(health.available && health.classifier);

  return (
    <main className="student">
      <div className="student-top">
        <Link href="/dashboard" className="link">
          ← Самбар
        </Link>
        <h1>Бодлого оруулах</h1>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="card wide">
        <h2>1. Зураг эсвэл текст</h2>
        {ocrOff && (
          <p className="reason">
            Зураг таних үйлчилгээ одоогоор ажиллахгүй байна — бодлогоо доор гараар бичээрэй.
          </p>
        )}
        <div className="row">
          <label className={`btn ${ocrOff ? "secondary" : ""}`} style={{ width: "auto" }}>
            📷 Зураг авах / сонгох
            <input
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              onChange={onFile}
              disabled={!!busy}
              style={{ display: "none" }}
            />
          </label>
          {upload && (
            <button type="button" className="btn danger small" onClick={removeImage}>
              Зургийг устгах
            </button>
          )}
        </div>
        <p className="hint">Нэг бодлого, тод, хэвлэмэл зураг хамгийн сайн танигдана. Зураг зөвхөн танд харагдана.</p>
        {preview && (
          // blob: URL — next/image хэрэггүй
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="Оруулсан бодлого" className="preview" />
        )}
        {upload?.message && <p className="hint">{upload.message}</p>}

        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="text">Бодлогын текст (томьёог $...$ дотор бичиж болно)</label>
          <textarea
            id="text"
            className="textarea"
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="жишээ: Тэгшитгэлийг бод. $x^2 - 7x + 12 = 0$"
            disabled={!!busy}
          />
        </div>
        {text.trim() && (
          <div className="statement" style={{ fontSize: 17 }}>
            <MathText text={text} />
          </div>
        )}
        <button className="btn" style={{ width: "auto", marginTop: 12 }} onClick={classify} disabled={!!busy || !text.trim()}>
          {busy || "Сэдвийг тодорхойлох"}
        </button>
      </div>

      {(result || clfOff) && (
        <div className="card wide">
          <h2>2. Сэдэв</h2>
          {result?.available && result.topic_id ? (
            <>
              <p>
                Систем энэ бодлогыг <strong>{result.topic_name}</strong> сэдэв гэж таамаглаж байна
                {result.confidence !== null && ` (итгэл ${Math.round(result.confidence * 100)}%)`}
                {result.difficulty && `, түвшин ${result.difficulty} · ${DIFFICULTY_LABEL[result.difficulty]}`}.
              </p>
              {result.subtopics.length > 0 && (
                <p className="hint">Дэд сэдэв: {result.subtopics.join(", ")}</p>
              )}
              {result.terms.length > 0 && (
                <p className="hint">Нэр томьёо: {result.terms.join(", ")} — дасгал дээр дарж тайлбар харна.</p>
              )}
            </>
          ) : (
            <p className="reason">Сэдэв ангилагч одоогоор ажиллахгүй байна — сэдвээ өөрөө сонгоно уу.</p>
          )}
          <div className="field">
            <label htmlFor="topic">Буруу бол сэдвээ засна уу</label>
            <select id="topic" className="select" value={chosenTopic} onChange={(e) => setChosenTopic(e.target.value)}>
              <option value="">— сэдэв сонгох —</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div className="row">
            <Link
              href={chosenTopic ? `/practice?topic=${encodeURIComponent(chosenTopic)}` : "#"}
              className="btn"
              aria-disabled={!chosenTopic}
              style={{ pointerEvents: chosenTopic ? "auto" : "none", opacity: chosenTopic ? 1 : 0.6 }}
            >
              Энэ сэдвээс ижил төстэй бодлого бодох →
            </Link>
          </div>
          <p className="hint" style={{ marginTop: 10 }}>
            Систем таны бодлогыг бодохгүй — ижил төрлийн бодлогыг алхам алхмаар хамт бодсоны дараа өөрийнхөө бодлогыг бие даан бодно.
          </p>
        </div>
      )}
    </main>
  );
}
