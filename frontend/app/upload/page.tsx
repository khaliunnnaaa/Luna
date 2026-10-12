"use client";

import Link from "next/link";
import { ChangeEvent, DragEvent, useEffect, useState } from "react";

import MathText from "@/components/MathText";
import Shell, { PageHead } from "@/components/Shell";
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

const MAX_BYTES = 10 * 1024 * 1024;

// FR-03: зураг (камер/файл) → OCR → засах; FR-04: сэдэв ангилах; NFR-07: ML-гүй бол гараар бичих.
export default function UploadPage() {
  const [health, setHealth] = useState<MlHealth | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadDetail | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<ClassifyResult | null>(null);
  const [chosenTopic, setChosenTopic] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [over, setOver] = useState(false);

  useEffect(() => {
    if (!getToken()) return; // Shell /login руу шилжүүлнэ
    api.get<MlHealth>("/ml/health").then(setHealth).catch(() => setHealth({ available: false, classifier: false, ocr: false }));
    api.get<Topic[]>("/topics").then(setTopics).catch(() => {});
  }, []);

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // ижил файлыг дахин сонгож болохоор
    if (file) onFile(file);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && !busy) onFile(file);
  }

  async function onFile(file: File) {
    setError("");
    // Backend-ийн хязгаарыг урьдчилан шалгаж, хүлээлгүй хариу өгнө
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setError("Зөвхөн JPG эсвэл PNG зураг оруулна уу.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("Зураг 10MB-аас бага байх ёстой.");
      return;
    }
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

  const similarHref = chosenTopic
    ? upload
      ? `/similar?upload=${upload.id}&topic=${encodeURIComponent(chosenTopic)}`
      : `/similar?text=${encodeURIComponent(text)}&topic=${encodeURIComponent(chosenTopic)}`
    : "#";
  const step = result || clfOff ? (chosenTopic ? 3 : 2) : 1;

  return (
    <Shell>
      <Link href="/dashboard" className="back">
        ← Нүүр рүү
      </Link>
      <PageHead eyebrow="Бодлого оруулах" title="Ямар бодлого дээр гацсан бэ?">
        Хэвлэмэл бодлогын тод зураг оруулах эсвэл доорх хэсэгт гараар бичээрэй. Систем таны бодлогыг
        бодохгүй — ижил төрлийн жишээг хамт бодсоны дараа өөрөө бодно.
      </PageHead>

      <div className="workspace">
        <ol className="steps-flow" aria-label="Алхмууд">
          {["01 Бодлого", "02 Сэдэв", "03 Хамт бодох"].map((t, i) => (
            <li key={t} className={step === i + 1 ? "on" : step > i + 1 ? "done" : ""}>
              {step > i + 1 ? "✓ " : ""}
              {t}
            </li>
          ))}
        </ol>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {ocrOff && (
          <p className="reason" style={{ marginBottom: 16 }}>
            Зураг таних үйлчилгээ одоогоор ажиллахгүй байна — бодлогоо доор гараар бичээрэй.
          </p>
        )}

        <label
          className={`drop ${over ? "over" : ""} ${busy ? "disabled" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={onDrop}
        >
          <div className="upload-icon" aria-hidden>
            {busy ? <span className="spinner" style={{ borderColor: "#e4d3c9", borderTopColor: "var(--rust)", width: 26, height: 26, display: "inline-block" }} /> : "▧"}
          </div>
          <h3>{busy || (upload ? "Зураг оруулсан" : "Зураг оруулах")}</h3>
          <p>JPG, PNG · 10MB хүртэл · чирж оруулж болно. Зураг зөвхөн танд харагдана.</p>
          <span className="btn light small">{upload ? "Өөр зураг сонгох" : "Зураг авах / сонгох"}</span>
          <input
            type="file"
            accept="image/jpeg,image/png"
            capture="environment"
            onChange={onPick}
            disabled={!!busy}
            className="sr-only"
          />
          {preview && (
            // blob: URL — next/image хэрэггүй
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Оруулсан бодлого" className="upload-preview" />
          )}
        </label>
        {upload && (
          <div className="actions" style={{ marginTop: 10, justifyContent: "space-between" }}>
            <span className="hint">{upload.message ?? "Танигдсан текстийг доор шалгаад засаарай."}</span>
            <button type="button" className="btn danger small" onClick={removeImage}>
              Зургийг устгах
            </button>
          </div>
        )}

        <div className="section-mini">
          <label htmlFor="text">{upload ? "Танигдсан текст — алдаа байвал засаарай" : "Эсвэл бодлогоо бичих"}</label>
        </div>
        <textarea
          id="text"
          className="textarea"
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Жишээ: Тэгшитгэлийг бод. $x^2 - 5x + 6 = 0$"
          disabled={!!busy}
          aria-describedby="text-help"
        />
        {text.trim() && (
          <div className="preview-math" aria-label="Урьдчилан харах">
            <MathText text={text} />
          </div>
        )}
        <p id="text-help" className="tiny" style={{ margin: "8px 0 0" }}>
          Томьёог <code>$...$</code> дотор бичвэл зөв харагдана: <code>{"$x^2 + 1$"}</code>,{" "}
          <code>{"$\\sqrt{2}$"}</code>, <code>{"$\\frac{1}{2}$"}</code>.
        </p>
        <div className="actions" style={{ marginTop: 18 }}>
          <button className="btn rust" onClick={classify} disabled={!!busy || !text.trim()}>
            {busy || "Сэдвийг тодорхойлох →"}
          </button>
        </div>

        {(result || clfOff) && (
          <>
            <hr className="rule" />
            <div className="section-label">
              <h2>Сэдэв</h2>
            </div>
            <div className="card">
              {result?.available && result.topic_id ? (
                <>
                  <p className="serif" style={{ fontSize: 22, lineHeight: 1.4, margin: "0 0 10px" }}>
                    Энэ бодлого <strong style={{ color: "var(--rust-dark)" }}>{result.topic_name}</strong> сэдвийнх бололтой.
                  </p>
                  <p className="hint" style={{ margin: "0 0 4px" }}>
                    {result.confidence !== null && `Итгэл ${Math.round(result.confidence * 100)}%`}
                    {result.difficulty && ` · ${DIFFICULTY_LABEL[result.difficulty]} түвшин`}
                    {result.subtopics.length > 0 && ` · ${result.subtopics.join(", ")}`}
                  </p>
                  {result.terms.length > 0 && (
                    <p className="hint" style={{ margin: 0 }}>Нэр томьёо: {result.terms.join(", ")}</p>
                  )}
                </>
              ) : (
                <p className="reason">Сэдэв ангилагч одоогоор ажиллахгүй байна — сэдвээ өөрөө сонгоно уу.</p>
              )}
              <div className="field" style={{ marginTop: 20 }}>
                <label htmlFor="topic">{result?.topic_id ? "Буруу бол сэдвээ засна уу" : "Сэдэв сонгох"}</label>
                <select id="topic" className="select" value={chosenTopic} onChange={(e) => setChosenTopic(e.target.value)}>
                  <option value="">— сэдэв сонгох —</option>
                  {topics.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="actions">
                <Link href={similarHref} className="btn rust" aria-disabled={!chosenTopic}>
                  Ижил бодлогыг хамт бодох →
                </Link>
                <Link
                  href={chosenTopic ? `/practice?topic=${encodeURIComponent(chosenTopic)}` : "#"}
                  className="btn light"
                  aria-disabled={!chosenTopic}
                >
                  Энэ сэдвээс дасгал
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}
