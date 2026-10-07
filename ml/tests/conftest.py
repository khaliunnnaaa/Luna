import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.common import MODELS_DIR  # noqa: E402

needs_models = pytest.mark.skipif(
    not (MODELS_DIR / "topic_clf.joblib").exists(),
    reason="загвар сургаагүй: python -m ml.classifier.train",
)
