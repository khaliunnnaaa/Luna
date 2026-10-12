"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getToken, logout, me, ROLE_LABEL, User } from "@/lib/api";

// Сурагчийн бүх хуудсанд нийтлэг толгой (лого, цэс, бүртгэл) ба хөл.
// Нэвтрээгүй бол /login руу шилжүүлнэ.
const NAV = [
  { href: "/dashboard", label: "Нүүр", match: ["/dashboard"] },
  { href: "/upload", label: "Бодлого оруулах", match: ["/upload", "/similar"] },
  { href: "/practice", label: "Дасгал", match: ["/practice", "/problems"] },
  { href: "/placement", label: "Түвшин тогтоох", match: ["/placement"] },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
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

  return (
    <div className="site">
      <a href="#main" className="skip">
        Үндсэн агуулга руу
      </a>
      <header className="top">
        <Link href="/dashboard" className="logo" aria-label="алхам — нүүр">
          алхам
        </Link>
        <nav className="menu" aria-label="Үндсэн цэс">
          {NAV.map((n) => {
            const current = n.match.some((m) => pathname.startsWith(m));
            return (
              <Link
                key={n.href}
                href={n.href}
                className={current ? "current" : ""}
                aria-current={current ? "page" : undefined}
              >
                {n.label}
              </Link>
            );
          })}
          {user?.role === "admin" && (
            <Link href="/admin/problems" className={pathname.startsWith("/admin") ? "current" : ""}>
              Админ
            </Link>
          )}
        </nav>
        <div className="account">
          {user && (
            <>
              <span className="account-name">
                {user.full_name}
                <small>{ROLE_LABEL[user.role]}</small>
              </span>
              <span className="portrait" aria-hidden>
                {user.full_name.trim().charAt(0).toUpperCase() || "?"}
              </span>
              <button type="button" className="logout" onClick={onLogout}>
                Гарах
              </button>
            </>
          )}
        </div>
      </header>
      <main className="wrap" id="main">
        {children}
        <footer className="foot">
          <span>алхам — математик сурахад туслах ухаалаг веб систем</span>
          <span>Хариу биш, чиглүүлэг.</span>
        </footer>
      </main>
    </div>
  );
}

// Хуудасны толгой: жижиг шошго, serif гарчиг, тайлбар.
export function PageHead({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-head">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </div>
  );
}

// Ачаалж байх үеийн саарал хэсгүүд (хоосон дэлгэцийн оронд).
export function Loading({ label = "Ачаалж байна..." }: { label?: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="skeleton" style={{ width: "40%" }} />
      <span className="skeleton" style={{ width: "85%" }} />
      <span className="skeleton" style={{ width: "65%" }} />
      <span className="sr-only">{label}</span>
    </div>
  );
}
