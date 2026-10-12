"use client";

import Link from "next/link";
import { useState } from "react";

import MathText from "@/components/MathText";

// Нэвтрэх / бүртгүүлэх хуудасны хоёр баганат загвар.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth">
      <aside className="auth-side">
        <Link href="/" className="logo">
          алхам
        </Link>
        <blockquote>Алдаа бол дараагийн алхмын дохио.</blockquote>
        <div className="math-line">
          <MathText text="$(x - 2)(x - 3) = 0$" />
        </div>
      </aside>
      <main className="auth-main" id="main">
        {children}
      </main>
    </div>
  );
}

// Нууц үгийн талбар — харах/нуух товчтой.
export function PasswordInput({
  id,
  value,
  onChange,
  autoComplete,
  describedBy,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  describedBy?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="pw">
      <input
        id={id}
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        autoComplete={autoComplete}
        aria-describedby={describedBy}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "Нууц үгийг нуух" : "Нууц үгийг харах"}
        aria-pressed={show}
      >
        {show ? "Нуух" : "Харах"}
      </button>
    </div>
  );
}
