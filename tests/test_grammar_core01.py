from pathlib import Path

import pytest
from lark import Lark, LarkError

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_PATH = ROOT / "grammar" / "sipl.lark"
POSITIVE_DIR = ROOT / "examples" / "positive"
NEGATIVE_DIR = ROOT / "examples" / "negative"


def make_parser() -> Lark:
    grammar_text = GRAMMAR_PATH.read_text(encoding="utf-8")
    return Lark(grammar_text, start="start", parser="earley", ambiguity="explicit")


POSITIVE_FILES = sorted(POSITIVE_DIR.glob("*.sipl"))
NEGATIVE_FILES = sorted(NEGATIVE_DIR.glob("*.sipl"))


def test_examples_count() -> None:
    assert len(POSITIVE_FILES) >= 10
    assert len(NEGATIVE_FILES) >= 10


@pytest.mark.parametrize("path", POSITIVE_FILES, ids=lambda p: p.name)
def test_positive_examples_parse(path: Path) -> None:
    parser = make_parser()
    tree = parser.parse(path.read_text(encoding="utf-8"))
    # Переконуємось, що граматика однозначна на всіх прикладах
    assert "_ambig" not in {t.data for t in tree.iter_subtrees()}


@pytest.mark.parametrize("path", NEGATIVE_FILES, ids=lambda p: p.name)
def test_negative_examples_fail(path: Path) -> None:
    parser = make_parser()
    with pytest.raises(LarkError):
        parser.parse(path.read_text(encoding="utf-8"))