import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import "katex/dist/katex.min.css";
import "./globals.css";

// DM Sans кирилл үсэггүй тул кирилл дэмждэг IBM Plex Sans-ийг үндсэн фонт болгов.
const sans = IBM_Plex_Sans({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
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
