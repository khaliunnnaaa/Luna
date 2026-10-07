// Backend API-тай харилцах туслах функцууд.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "token";

export type Role = "student" | "parent" | "admin";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
};

type TokenResponse = { access_token: string; token_type: string; user: User };

export const ROLE_LABEL: Record<Role, string> = {
  student: "Сурагч",
  parent: "Эцэг эх",
  admin: "Админ",
};

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {}
}

export function logout() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {}
}

// FastAPI-ийн алдааны хариуг ойлгомжтой нэг өгүүлбэр болгоно.
function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const msg = String(detail[0]?.msg ?? "");
    return msg.replace(/^Value error,\s*/, "") || "Мэдээлэл буруу байна";
  }
  return status >= 500 ? "Серверт алдаа гарлаа" : "Алдаа гарлаа";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new Error("Сервертэй холбогдож чадсангүй. Backend асаалттай эсэхийг шалгана уу.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(body, res.status));
  return body as T;
}

export async function register(data: {
  email: string;
  password: string;
  full_name: string;
  role: Role;
}): Promise<User> {
  const r = await request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setToken(r.access_token);
  return r.user;
}

export async function login(email: string, password: string): Promise<User> {
  const r = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(r.access_token);
  return r.user;
}

export function me(): Promise<User> {
  return request<User>("/auth/me");
}

// ---------- Ерөнхий хүсэлтүүд ----------
export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  del: (path: string) => request<null>(path, { method: "DELETE" }),
};

// ---------- Контент (FR-16) ----------
export type Topic = {
  id: string;
  name: string;
  grade: number;
  description: string | null;
  prerequisites: string[];
  problem_count: number;
};

export type Term = {
  id: number;
  term: string;
  explanation: string;
  example: string | null;
  topic_id: string | null;
};

export type Problem = {
  id: number;
  code: string | null;
  topic_id: string;
  subtopic: string | null;
  difficulty: number; // 1–3
  statement: string;
  answers: string[];
  hints: string[];
  common_mistakes: string | null;
  terms: string[];
  source: string | null;
};
