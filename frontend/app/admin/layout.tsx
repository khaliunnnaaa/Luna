"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getToken, logout, me, User } from "@/lib/api";

const TABS = [
  { href: "/admin/problems", label: "Бодлого" },
  { href: "/admin/topics", label: "Сэдэв" },
  { href: "/admin/terms", label: "Нэр томьёо" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    me()
      .then((u) => (u.role === "admin" ? setUser(u) : router.replace("/dashboard")))
      .catch(() => {
        logout();
        router.replace("/login");
      });
  }, [router]);

  if (!user) return <main className="page"><p className="subtitle">Ачаалж байна...</p></main>;

  return (
    <main className="admin">
      <div className="admin-top">
        <h1>Админ · Контент удирдлага</h1>
        <button
          className="btn secondary small"
          onClick={() => {
            logout();
            router.push("/");
          }}
        >
          Гарах ({user.full_name})
        </button>
      </div>
      <nav className="tabs">
        {TABS.map((t) => (
          <Link key={t.href} href={t.href} className={`tab ${pathname === t.href ? "active" : ""}`}>
            {t.label}
          </Link>
        ))}
      </nav>
      {children}
    </main>
  );
}
