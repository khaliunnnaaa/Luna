"""Командын мөрийн демо: нэг зохиомол сурагчаар бүх модулийг дараалан харуулна.

    python demo.py

1. Бодлого ангилах  2. Хариулт оруулж mastery өөрчлөгдөхийг харах  3. Дараагийн бодлого санал болгох
Сурагчийн төлөв: state/students/demo_student.json (демо эхлэх бүрт шинэчлэгдэнэ).
"""
import random

from ml import api
from ml.common import COL_ID, COL_LATEX, COL_TEXT, SEED, load_bank, load_topics

STUDENT = "demo_student"


def line(title=""):
    print("\n" + "─" * 70 + (f"\n{title}" if title else ""))


def main():
    random.seed(SEED)
    topics = load_topics()
    bank = load_bank().set_index(COL_ID)

    line("1. Бодлого ангилах (FR-04)")
    samples = [
        "Тэгшитгэлийг бод. \\log_3(x-1)=2",
        "Тэнцэтгэл бишийг бод. x^2-9<0",
        "Шоог хоёр удаа хаяхад хоёуланд нь 6 буух магадлалыг ол.",
        "f(x) = x^2 - 2x функцийн оройн координатыг ол.",
    ]
    for text in samples:
        r = api.classify_problem(text)
        print(f"  {text}\n    → {r['topic']} ({topics[r['topic']].name}), түвшин {r['difficulty']}, итгэл {r['confidence']:.2f}")

    line("2. Сурагч бүртгэх (10-р анги) ба анхны mastery")
    api._store.directory.joinpath(f"{STUDENT}.json").unlink(missing_ok=True)
    state = api.register_student(STUDENT, grade=10)
    print("  " + ", ".join(f"{k}={v:.2f}" for k, v in state["mastery"].items()))

    line("3. Санал болгох → хариулах → mastery шинэчлэх (12 алхам)")
    # Зохиомол сурагч: эхэндээ ихэвчлэн зөв, алдаа ч гаргана
    answers = [True, True, False, True, True, True, False, True, True, True, True, True]
    for step, correct in enumerate(answers, 1):
        rec = api.recommend_next(STUDENT)
        before = api._store.load(STUDENT)["mastery"][rec["topic"]]
        mastery = api.update_mastery(STUDENT, rec["topic"], correct)
        p = bank.loc[rec["problem_id"]]
        print(f"\n  [{step:2d}] {rec['problem_id']} ({rec['topic']}, түвшин {rec['difficulty']}): "
              f"{p[COL_TEXT]}  {p[COL_LATEX]}")
        print(f"       шалтгаан: {rec['reason']}")
        print(f"       хариулт: {'✓ зөв ' if correct else '✗ буруу'}   "
              f"{rec['topic']} mastery {before:.3f} → {mastery[rec['topic']]:.3f}")

    line("4. Эцсийн төлөв ба дараагийн санал")
    final = api._store.load(STUDENT)["mastery"]
    for code, m in final.items():
        bar = "█" * int(m * 30)
        print(f"  {code} {topics[code].name:30s} {m:.3f} {bar}{'  ✓ эзэмшсэн' if m >= 0.95 else ''}")
    nxt = api.recommend_next(STUDENT)
    print(f"\n  Дараагийн бодлого: {nxt['problem_id']} ({nxt['topic']})\n  {nxt['reason']}")


if __name__ == "__main__":
    main()
