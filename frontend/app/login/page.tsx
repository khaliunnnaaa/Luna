"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <form className="card" onSubmit={onSubmit}>
        <h1>Нэвтрэх</h1>
        <p className="subtitle">Тавтай морил! Үргэлжлүүлэн сурцгаая.</p>

        {error && <div className="error">{error}</div>}

        <div className="field">
          <label htmlFor="email">Имэйл</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>

        <div className="field">
          <label htmlFor="password">Нууц үг</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>

        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Түр хүлээнэ үү..." : "Нэвтрэх"}
        </button>

        <p className="switch">
          Бүртгэлгүй юу? <Link href="/register">Бүртгүүлэх</Link>
        </p>
      </form>
    </main>
  );
}
