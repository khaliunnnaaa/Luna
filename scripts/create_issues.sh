#!/usr/bin/env bash
# Баримт бичгийн FR-01…FR-16-г GitHub issue болгоно.
# Шаардлага: gh CLI суулгаж, `gh auth login` хийсэн байх. Repo-гийн root дээрээс ажиллуулна.
set -euo pipefail

for l in "Must:d73a4a" "Should:fbca04" "Could:0e8a16" "backend:1d76db" "frontend:5319e7" "ml:b60205" "data:c5def5"; do
  gh label create "${l%%:*}" --color "${l##*:}" --force >/dev/null
done

issue() { gh issue create --title "$1" --label "$2" --body "$3" >/dev/null && echo "✓ $1"; }

issue "FR-01 Бүртгэл ба нэвтрэлт (3 эрх)"            "Must,backend,frontend" "Сурагч, эцэг эх, админ эрхтэй бүртгэл/нэвтрэлт. JWT, argon2 hash."
issue "FR-02 Түвшин тогтоох adaptive тест"           "Must,backend,frontend" "8–10 асуулт, ≤10 минут, сэдэв тус бүрийн анхны түвшин."
issue "FR-03 Бодлогын зураг оруулах + OCR"           "Must,ml,frontend"      "Камер/файл, OCR (Tesseract mon + pix2tex), үр дүнг засах боломж. ≤5 сек."
issue "FR-04 Бодлогын сэдэв ангилах"                 "Must,ml"               "TF-IDF+LogReg суурь → BERT. Accuracy ≥ 80%."
issue "FR-05 Нэр томьёо тайлбарлах"                  "Must,frontend,backend" "Үг дээр дарахад тайлбар+жишээ; дарсныг term_clicks-д бүртгэх."
issue "FR-06 Алхамчилсан зааварчилгаа (3 шатны hint)" "Must,backend,frontend" "Бэлэн хариу өгөхгүй. Алхам бүр 2–3 өгүүлбэр."
issue "FR-07 Ижил төстэй бодлогоор тайлбарлах"       "Must,backend"          "Ижил төрлийн бодлогыг алхамчлан харуулаад, сурагч өөрийнхөө бодлогыг бодно."
issue "FR-08 Мэдлэгийн цоорхой тодорхойлох"          "Must,ml"               "Хариулт, hint, дарсан нэр томьёо + BKT. AUC ≥ 0.70."
issue "FR-09 Түвшинд тохирсон дасгал санал болгох"   "Must,backend,ml"       "Prerequisite граф + BKT дээр суурилсан санал болгогч."
issue "FR-10 Хариу шалгах (SymPy)"                   "Must,backend"          "Тоон/алгебрийн эквивалент (1/2 = 0.5), алдааны төрөл тэмдэглэх."
issue "FR-11 Сэдвийн уялдаа холбооны зам"            "Should,frontend"       "Prerequisite графыг харуулах, эхлэх сэдвээ сонгох."
issue "FR-12 Сурагчийн ахицын самбар"                "Should,frontend"       "Эзэмшлийн түвшин, бодсон тоо, ахицын график."
issue "FR-13 Урамшуулал (оноо, badge, streak)"        "Should,backend,frontend" "Оноо, цол тэмдэг, тасралтгүй өдрийн тоо."
issue "FR-14 Эцэг эхийн самбар"                      "Should,frontend,backend" "Хүүхэдтэй холбогдох, ахиц/сул тал, хамт бодох зөвлөмж."
issue "FR-15 Ижил түвшний өрсөлдөөн"                 "Could,frontend,backend" "Долоо хоногийн оноон жагсаалт, badge илгээх."
issue "FR-16 Контент удирдлага (админ)"              "Must,backend,frontend" "Бодлого, сэдэв, нэр томьёо, холбоосын CRUD."
issue "DATA Сэдвийн граф, нэр томьёо, бодлогын сан"   "Must,data"             "15–20 сэдвийн граф, толь, бодлогын санг багштай хамт бүрдүүлэх."
issue "DATA OCR зургийн багц (≥300, зураг↔LaTeX)"     "Must,data,ml"          "Зураг авах, LaTeX-ээр шошголох, train/val/test хуваах."
