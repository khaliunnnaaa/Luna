"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { register, Role } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("student");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Нууц үг дор хаяж 8 тэмдэгт байх ёстой");
      return;
    }
    setLoading(true);
    try {
      await register({ email, password, full_name: fullName, role });
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
        <h1>Бүртгүүлэх</h1>
        <p className="subtitle">Хэдхэн секундэд бүртгэлээ үүсгээрэй.</p>

        {error && <div className="error">{error}</div>}

        <div className="field">
          <label>Би</label>
          <div className="roles">
            <button
              type="button"
              className={`role ${role === "student" ? "active" : ""}`}
              onClick={() => setRole("student")}
            >
              Сурагч
            </button>
            <button
              type="button"
              className={`role ${role === "parent" ? "active" : ""}`}
              onClick={() => setRole("parent")}
            >
              Эцэг эх
            </button>
          </div>
        </div>

        <div className="field">
          <label htmlFor="name">Нэр</label>
          <input
            id="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoComplete="name"
          />
        </div>

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
            autoComplete="new-password"
          />
          <span className="hint">Дор хаяж 8 тэмдэгт</span>
        </div>

        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Түр хүлээнэ үү..." : "Бүртгүүлэх"}
        </button>

        <p className="switch">
          Бүртгэлтэй юу? <Link href="/login">Нэвтрэх</Link>
        </p>
      </form>
    </main>
  );
}
