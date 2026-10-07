"use client";

import katex from "katex";
import { Fragment } from "react";

// "Бод: $x^2 - 5x + 6 = 0$" гэх мэт текстийг томьёотой нь харуулна.
// $...$ доторх хэсгийг KaTeX-ээр зурна, бусдыг энгийн текстээр.
export default function MathText({ text }: { text: string }) {
  const parts = text.split(/(\$[^$]+\$)/g);
  return (
    <span>
      {parts.map((part, i) => {
        if (part.length > 2 && part.startsWith("$") && part.endsWith("$")) {
          const html = katex.renderToString(part.slice(1, -1), { throwOnError: false });
          return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
        }
        return <Fragment key={i}>{part}</Fragment>;
      })}
    </span>
  );
}
