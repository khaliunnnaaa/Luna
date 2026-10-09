"""FR-09/FR-11: Дараагийн дасгал санал болгогч — ML хэсгийн `ml/recommender/recommend.py`-ийн
дүрмийг өгөгдлийн сан дээр ажилладаг болгосон хувилбар.

Логик:
  1. Урьдач сэдвүүд нь бүгд эзэмшигдсэн (mastery ≥ 0.95) боловч өөрөө эзэмшигдээгүй сэдвүүд
     "нээлттэй". Тэдгээрээс топологийн (prerequisite) дарааллаар эхнийхийг сонгоно.
  2. Бүх сэдэв эзэмшигдсэн бол хамгийн бага mastery-тэй сэдвээр давтлага.
  3. Сэдвийн mastery-д тохирох түвшин (<0.5 → 1, <0.8 → 2, бусад → 3)-д хамгийн ойр,
     сурагчийн бодоогүй бодлогыг сонгоно; бүгдийг бодсон бол хамгийн эрт бодсоныг давтана.
"""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Problem, Topic
from app.models.learning import Attempt
from app.services import mastery as mastery_svc


def topological_order(prereqs: Dict[str, List[str]]) -> List[str]:
    """Kahn-ийн алгоритм. Цикл байвал (админ API зөвшөөрдөггүй ч) үлдсэнийг ард нь залгана."""
    indegree = {c: len(ps) for c, ps in prereqs.items()}
    children: Dict[str, List[str]] = {c: [] for c in prereqs}
    for c, ps in prereqs.items():
        for p in ps:
            children.setdefault(p, []).append(c)
    queue = sorted(c for c, d in indegree.items() if d == 0)
    order: List[str] = []
    while queue:
        c = queue.pop(0)
        order.append(c)
        for ch in sorted(children.get(c, [])):
            indegree[ch] -= 1
            if indegree[ch] == 0:
                queue.append(ch)
        queue.sort()
    return order + sorted(set(prereqs) - set(order))


def target_difficulty(p_mastery: float) -> int:
    if p_mastery < 0.5:
        return 1
    if p_mastery < 0.8:
        return 2
    return 3


def choose_topic(
    topics: Dict[str, Topic], mastery: Dict[str, float], preferred: Optional[str] = None
) -> Tuple[str, str]:
    """-> (сэдвийн код, шалтгаан). `preferred` өгвөл (FR-11: сурагч өөрөө сонгосон) түүнийг авна."""
    thr = mastery_svc.MASTERED
    if preferred and preferred in topics:
        return preferred, f"Та {topics[preferred].name} сэдвийг сонгосон."
    prereqs = {c: [p.id for p in t.prerequisites] for c, t in topics.items()}
    order = topological_order(prereqs)
    mastered = {c: mastery.get(c, 0.0) >= thr for c in topics}
    open_topics = [c for c in order if not mastered[c] and all(mastered[p] for p in prereqs[c])]
    if open_topics:
        c = open_topics[0]
        base = f"{topics[c].name}: эзэмшил {mastery.get(c, 0.0):.0%}."
        if prereqs[c]:
            names = ", ".join(topics[p].name for p in prereqs[c])
            return c, f"{base} Өмнөх сэдэв ({names}) эзэмшигдсэн тул дараагийн алхам."
        return c, f"{base} Урьдач сэдэвгүй суурь сэдэв."
    c = min(topics, key=lambda x: (mastery.get(x, 0.0), x))
    return c, f"Бүх сэдэв эзэмшигдсэн. Хамгийн бага эзэмшилтэй {topics[c].name}-ээр давтлага."


def pick_problem(
    db: Session, user_id: int, topic_id: str, difficulty: int
) -> Optional[Problem]:
    problems = list(db.scalars(select(Problem).where(Problem.topic_id == topic_id)))
    if not problems:
        return None
    # Сурагчийн оролдлогууд: {problem_id: (зөв бодсон эсэх, хамгийн сүүлийн оролдлогын id)}
    rows = db.execute(
        select(Attempt.problem_id, func.max(Attempt.is_correct), func.max(Attempt.id))
        .where(Attempt.user_id == user_id, Attempt.topic_id == topic_id)
        .group_by(Attempt.problem_id)
    ).all()
    seen = {pid: (bool(solved), last) for pid, solved, last in rows}

    def key(p: Problem):
        solved, last = seen.get(p.id, (False, 0))
        attempted = p.id in seen
        # 1) бодоогүй → 2) оролдсон ч бодоогүй → 3) бодсон;
        # дараа нь түвшний ойр байдал, хуучин нь түрүүнд
        return (solved, attempted, abs(p.difficulty - difficulty), last, p.id)

    return min(problems, key=key)


def recommend(
    db: Session, user_id: int, preferred_topic: Optional[str] = None
) -> Tuple[Optional[Problem], str, str, int]:
    """-> (бодлого | None, сэдвийн код, шалтгаан, зорилтот түвшин)"""
    topics = {t.id: t for t in db.scalars(select(Topic))}
    if not topics:
        return None, "", "Сэдэв бүртгэгдээгүй байна.", 1
    rows = mastery_svc.all_for_user(db, user_id)
    mastery = {
        c: (rows[c].p_mastery if c in rows else mastery_svc.params_for(c)["prior"]) for c in topics
    }
    topic_id, reason = choose_topic(topics, mastery, preferred_topic)
    level = target_difficulty(mastery[topic_id])
    problem = pick_problem(db, user_id, topic_id, level)
    if problem is None:
        return None, topic_id, reason + " Энэ сэдэвт бодлого алга.", level
    if problem.difficulty != level:
        reason += f" Тохирох түвшин {level}, хамгийн ойр нь {problem.difficulty}."
    else:
        reason += f" Түвшин {level}."
    return problem, topic_id, reason, level
