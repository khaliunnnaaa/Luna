"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import AuthLayout, { PasswordInput } from "@/components/AuthLayout";
import { getToken, homeFor, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Аль хэдийн нэвтэрсэн бол шууд самбар руу
  useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const u = await login(email.trim(), password);
      router.push(homeFor(u.role));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={onSubmit}>
        <div className="eyebrow">Тавтай морил</div>
        <h1>Нэвтрэх</h1>
        <p className="subtitle">Өчигдөр зогссон газраасаа үргэлжлүүлье.</p>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}

        <div className="field">
          <label htmlFor="email">Имэйл</label>
          <input
            id="email"
            type="email"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
          />
        </div>

        <div className="field">
          <label htmlFor="password">Нууц үг</label>
          <PasswordInput id="password" value={password} onChange={setPassword} autoComplete="current-password" />
        </div>

        <button className="btn rust block" type="submit" disabled={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden /> Нэвтэрч байна...
            </>
          ) : (
            "Нэвтрэх →"
          )}
        </button>

        <p className="switch">
          Бүртгэлгүй юу? <Link href="/register">Бүртгүүлэх</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
