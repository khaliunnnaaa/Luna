"""FR-14: эцэг эхэд зориулсан хүүхдийн ахицын тайлан ба хамт бодоход зориулсан зөвлөмж.

`build_report` нь DB-гүй цэвэр функц (тестлэхэд амар): оролдлогууд + сэдвийн эзэмшлээс
- summary   — гол тоонууд (7 хоног, 14 хоног)
- activity  — сүүлийн 14 өдрийн зөв/буруу оролдлого (баганан график)
- trend     — сүүлийн 30 өдрийн дундаж эзэмшил (шугаман график)
- errors    — алдааны төрөл (FR-10)
- focus     — анхаарах сэдвүүд
- tips      — дүрэмд суурилсан зөвлөмж (хариу биш, хэрхэн хамт суух)
Өдрийг Улаанбаатарын цагаар (UTC+8, зуны цаггүй) тоолно.
"""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List, Optional

UB = timezone(timedelta(hours=8))
ACTIVITY_DAYS = 14
TREND_DAYS = 30

ERROR_LABEL = {
    "sign_error": "Тэмдгийн алдаа",
    "partial": "Шийд дутуу",
    "unparsable": "Бичих хэлбэр буруу",
    "wrong": "Буруу хариу",
    "empty": "Хоосон хариу",
}

ERROR_TIP = {
    "sign_error": "Тэмдгийн алдаа (сөрөг тоо, хаалт задлах, тал солих) олон байна. Бодолт бүрийн "
    "дараа «тэмдэг зөв үү?» гэж хамт шалгах дадал суулгаарай.",
    "partial": "Олон шийдтэй бодлогод нэг шийдээ л олоод зогсож байна. «Өөр шийд байж болох уу?» "
    "гэж асууж, бүх шийдийг орлуулж шалгуулаарай.",
    "unparsable": "Хариугаа системд буруу хэлбэрээр оруулж байна. Олон шийдийг [3, 4], бутархайг "
    "1/2 гэж бичихийг хамт давтаарай.",
}


def _local_day(dt: datetime) -> date:
    if dt.tzinfo is None:  # SQLite naive datetime-ийг UTC гэж үзнэ
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(UB).date()


def _pct(x: float) -> int:
    return round(x * 100)


def build_report(
    child_name: str,
    attempts: Iterable,  # Attempt-тэй ижил атрибуттай объектууд, created_at өсөх дарааллаар
    mastery: List[dict],  # services.mastery.overview(...)
    now: datetime,
    placement_done: bool,
) -> dict:
    attempts = sorted(attempts, key=lambda a: a.created_at)
    today = _local_day(now)
    names = {m["topic_id"]: m["name"] for m in mastery}

    # ---------- summary ----------
    week = [a for a in attempts if (today - _local_day(a.created_at)).days < 7]
    correct_7d = sum(a.is_correct for a in week)
    days14 = {
        _local_day(a.created_at) for a in attempts if (today - _local_day(a.created_at)).days < 14
    }
    last = attempts[-1].created_at if attempts else None
    summary = {
        "topics_total": len(mastery),
        "topics_mastered": sum(m["mastered"] for m in mastery),
        "attempts_total": len(attempts),
        "attempts_7d": len(week),
        "correct_7d": correct_7d,
        "accuracy_7d": round(correct_7d / len(week), 3) if week else None,
        "active_days_14": len(days14),
        "days_since_active": (today - _local_day(last)).days if last else None,
        "placement_done": placement_done,
    }

    # ---------- activity: 14 өдөр, зөв/буруу ----------
    per_day: dict = {}
    for a in attempts:
        d = _local_day(a.created_at)
        c = per_day.setdefault(d, [0, 0])
        c[0 if a.is_correct else 1] += 1
    activity = []
    for i in range(ACTIVITY_DAYS - 1, -1, -1):
        d = today - timedelta(days=i)
        ok, bad = per_day.get(d, (0, 0))
        activity.append({"date": d.isoformat(), "correct": ok, "wrong": bad})

    # ---------- trend: 30 өдрийн дундаж эзэмшил ----------
    # Оролдоогүй сэдэв — одоогийн утга (prior/placement); оролдсон сэдэв — эхний оролдлогын
    # mastery_before-оос эхэлж, өдөр бүрийн сүүлийн mastery_after-аар шинэчилнэ.
    state = {m["topic_id"]: m["p_mastery"] for m in mastery}
    first_seen: set = set()
    for a in attempts:
        if a.topic_id in state and a.topic_id not in first_seen and a.mastery_before is not None:
            state[a.topic_id] = a.mastery_before
            first_seen.add(a.topic_id)
    start = today - timedelta(days=TREND_DAYS - 1)
    trend, idx = [], 0
    for i in range(TREND_DAYS):
        d = start + timedelta(days=i)
        while idx < len(attempts) and _local_day(attempts[idx].created_at) <= d:
            a = attempts[idx]
            if a.topic_id in state and a.mastery_after is not None:
                state[a.topic_id] = a.mastery_after
            idx += 1
        avg = sum(state.values()) / len(state) if state else 0.0
        trend.append({"date": d.isoformat(), "avg_mastery": round(avg, 4)})

    # ---------- errors (30 өдөр) ----------
    recent = [a for a in attempts if (today - _local_day(a.created_at)).days < 30]
    err = Counter(a.error_type for a in recent if not a.is_correct and a.error_type)
    errors = [{"type": t, "label": ERROR_LABEL.get(t, t), "count": n} for t, n in err.most_common()]
    hints_avg = round(sum(a.hints_used for a in recent) / len(recent), 2) if recent else None

    # ---------- focus: оролдсон боловч эзэмшээгүй, хамгийн бага эзэмшилтэй ----------
    focus = sorted(
        (m for m in mastery if m["attempts_count"] > 0 and not m["mastered"]),
        key=lambda m: m["p_mastery"],
    )[:3]
    by_id = {m["topic_id"]: m for m in mastery}
    focus_out = [
        {
            "topic_id": m["topic_id"],
            "name": m["name"],
            "p_mastery": m["p_mastery"],
            "accuracy": round(m["correct_count"] / m["attempts_count"], 3),
            "weak_prerequisites": [
                names[p] for p in m["prerequisites"] if p in by_id and not by_id[p]["mastered"]
            ],
        }
        for m in focus
    ]

    tips = _tips(child_name, summary, focus_out, errors, hints_avg)
    return {
        "summary": summary,
        "activity": activity,
        "trend": trend,
        "mastery": mastery,
        "errors": errors,
        "hints_avg": hints_avg,
        "focus": focus_out,
        "tips": tips,
    }


def _tip(kind: str, title: str, text: str) -> dict:
    return {"kind": kind, "title": title, "text": text}


def _tips(
    name: str, s: dict, focus: List[dict], errors: List[dict], hints_avg: Optional[float]
) -> List[dict]:
    """Хамгийн хэрэгтэй 4 зөвлөмж. Хариуг хэлэх биш — хүүхдийг өөрөө бодоход нь дэмжих."""
    tips: List[dict] = []
    if not s["placement_done"]:
        tips.append(_tip(
            "start", "Түвшин тогтоох тест",
            f"{name} түвшин тогтоох тест өгөөгүй байна. 10 минутын тестийг хамт "
            "эхлүүлбэл систем түүнд тохирох дасгалыг сонгож эхэлнэ.",
        ))
    if s["attempts_total"] == 0:
        tips.append(_tip(
            "start", "Эхний алхам",
            f"{name} одоохондоо бодлого бодоогүй байна. Өдөрт 10–15 минутаар "
            "эхлүүлэхэд хамт суугаарай.",
        ))
        return tips[:4]
    idle = s["days_since_active"]
    if idle is not None and idle >= 3:
        tips.append(_tip(
            "habit", "Тогтмол дадал",
            f"Сүүлийн {idle} өдөр дасгал хийгээгүй байна. Өдөр бүр 15 минут тогтмол "
            "хийх нь долоо хоногт нэг удаа удаан хийснээс үр дүнтэй.",
        ))
    if focus:
        f = focus[0]
        text = (
            f"«{f['name']}» сэдэв дээр хамт суугаарай: бодлогыг хүүхдээрээ чангаар "
            "тайлбарлуулж, хаана гацаж байгааг сонсоорой. Хариуг нь хэлэхгүй байх нь чухал."
        )
        if f["weak_prerequisites"]:
            text += (
                f" Энэ сэдэв «{f['weak_prerequisites'][0]}»-д тулгуурладаг тул "
                "түүнийг давтах нь зүйтэй."
            )
        tips.append(_tip("focus", "Анхаарах сэдэв", text))
    if errors and errors[0]["type"] in ERROR_TIP and errors[0]["count"] >= 2:
        tips.append(_tip("error", errors[0]["label"], ERROR_TIP[errors[0]["type"]]))
    if hints_avg is not None and hints_avg >= 2:
        tips.append(_tip(
            "hints", "Сануулгад найдаж байна",
            "Бодлого бүрт дунджаар 2-оос олон сануулга авч байна. Эхний сануулгын дараа "
            "2–3 минут өөрөө бодуулж, дараа нь л дараагийнхыг нээгээрэй.",
        ))
    acc = s["accuracy_7d"]
    if acc is not None and acc >= 0.8 and s["attempts_7d"] >= 5:
        tips.append(_tip(
            "praise", "Сайн ахиж байна",
            f"Энэ долоо хоногт {_pct(acc)}% зөв хариулсан. Хичээл зүтгэлийг нь магтаж, "
            "шинэ сэдэв рүү урамшуулаарай.",
        ))
    return tips[:4]
