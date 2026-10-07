"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getToken, logout, me, ROLE_LABEL, User } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    me()
      .then(setUser)
      .catch(() => {
        logout();
        router.replace("/login");
      });
  }, [router]);

  function onLogout() {
    logout();
    router.push("/");
  }

  if (!user) {
    return (
      <main className="page">
        <p className="subtitle">Ачаалж байна...</p>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="card">
        <span className="badge">{ROLE_LABEL[user.role]}</span>
        <h1 style={{ marginTop: 12 }}>Сайн уу, {user.full_name}!</h1>
        <p className="subtitle">{user.email}</p>
        <p>Энд удахгүй таны самбар (ахиц, дасгал, бодлого) гарч ирнэ.</p>
        <div className="stack">
          {user.role === "admin" && (
            <Link href="/admin" className="btn">
              Контент удирдлага
            </Link>
          )}
          <button className="btn secondary" onClick={onLogout}>
            Гарах
          </button>
        </div>
      </div>
    </main>
  );
}
