"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import AuthLayout, { PasswordInput } from "@/components/AuthLayout";
import { register, Role } from "@/lib/api";

const ROLES: { value: Role; label: string; note: string }[] = [
  { value: "student", label: "Сурагч", note: "Бодлого бодож сурна" },
  { value: "parent", label: "Эцэг эх", note: "Хүүхдийнхээ ахицыг харна" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("student");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const pwShort = password.length > 0 && password.length < 8;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Нууц үг дор хаяж 8 тэмдэгт байх ёстой");
      return;
    }
    setLoading(true);
    try {
      await register({ email: email.trim(), password, full_name: fullName.trim(), role });
      // Шинэ сурагч эхлээд түвшнээ тогтооно
      router.push(role === "student" ? "/placement" : "/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={onSubmit}>
        <div className="eyebrow">Шинэ бүртгэл</div>
        <h1>Бүртгүүлэх</h1>
        <p className="subtitle">Хэдхэн секунд. Дараа нь 10 минутын түвшин тогтоох тестээр эхэлнэ.</p>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}

        <div className="field">
          <span className="field-label" id="role-label" style={{ fontSize: 13, fontWeight: 700 }}>
            Би
          </span>
          <div className="roles" role="radiogroup" aria-labelledby="role-label">
            {ROLES.map((r) => (
              <button
                key={r.value}
                type="button"
                role="radio"
                aria-checked={role === r.value}
                className={`role ${role === r.value ? "active" : ""}`}
                onClick={() => setRole(r.value)}
              >
                {r.label}
                <small>{r.note}</small>
              </button>
            ))}
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
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>

        <div className="field">
          <label htmlFor="password">Нууц үг</label>
          <PasswordInput
            id="password"
            value={password}
            onChange={setPassword}
            autoComplete="new-password"
            describedBy="pw-hint"
          />
          <span id="pw-hint" className="hint" style={pwShort ? { color: "var(--error)" } : undefined}>
            {pwShort ? `Дахиад ${8 - password.length} тэмдэгт` : "Дор хаяж 8 тэмдэгт"}
          </span>
        </div>

        <button className="btn rust block" type="submit" disabled={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden /> Бүртгэж байна...
            </>
          ) : (
            "Бүртгүүлэх →"
          )}
        </button>

        <p className="switch">
          Бүртгэлтэй юу? <Link href="/login">Нэвтрэх</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
