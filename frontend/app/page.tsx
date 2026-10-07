import Link from "next/link";

export default function Home() {
  return (
    <main className="page">
      <div className="card">
        <h1>Ухаалаг математик</h1>
        <p className="subtitle">Хариу биш, чиглүүлэг. Бодлогоо оруулаад алхам алхмаар өөрөө бод.</p>
        <div className="stack">
          <Link href="/register" className="btn">
            Бүртгүүлэх
          </Link>
          <Link href="/login" className="btn secondary">
            Нэвтрэх
          </Link>
        </div>
      </div>
    </main>
  );
}
