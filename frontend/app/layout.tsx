import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ухаалаг математик",
  description: "Математик сурахад туслах ухаалаг веб систем",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="mn">
      <body>{children}</body>
    </html>
  );
}
