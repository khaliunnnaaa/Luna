"""Сэдвийн prerequisite графтай ажиллах туслах функцууд."""

from typing import Dict, Iterable, List


def creates_cycle(graph: Dict[str, List[str]], topic_id: str, new_prereqs: Iterable[str]) -> bool:
    """`topic_id`-д `new_prereqs`-ийг өмнөх сэдэв болгоход тойрог үүсэх эсэх.

    graph: {сэдэв: [түүний өмнөх сэдвүүд]}
    Тойрог гэдэг нь A → B → A гэх мэт, сурагч хаанаас ч эхэлж чадахгүй байдал.
    """
    stack = list(new_prereqs)
    seen = set()
    while stack:
        current = stack.pop()
        if current == topic_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, []))
    return False
