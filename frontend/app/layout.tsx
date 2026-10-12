import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";
import "katex/dist/katex.min.css";
import "./globals.css";

// Nunito — дугуй хэлбэртэй, найрсаг, кирилл үсэгтэй (хатуу serif/editorial мэдрэмжээс зайлсхийх)
const sans = Nunito({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "алхам — Математикаа ойлгох орон зай",
  description: "Хариу биш, чиглүүлэг. Математик сурахад туслах ухаалаг веб систем.",
};

export const viewport: Viewport = {
  themeColor: "#f7f6f2",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="mn" className={sans.variable}>
      <body>{children}</body>
    </html>
  );
}
