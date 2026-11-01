"""What the text check covers. It reads words only; what it cannot see is written in studio/worldkit/safety.py and the guide."""
import pytest

from studio.worldkit import safety


@pytest.mark.parametrize("text", ["a nude figure", "NSFW", "erotic scene", "a child in a bikini", "bikini on a teenage girl", "schoolgirl in lingerie", "a 15 year old in underwear", "kid, shirtless"])
def test_refused(text):
    assert safety.text_problem(text) == safety.REFUSED


@pytest.mark.parametrize("text", ["rainy downtown block at night", "a children's playground at noon", "beach café interior", "a red sports car", "a bare brick wall", "a swimsuit on a mannequin", "Essex high street"])
def test_allowed(text):
    assert safety.text_problem(text) == ""


def test_it_reads_nested_values_and_across_fields():
    assert safety.text_problem({"a": ["fine", {"b": "explicit"}]}) == safety.REFUSED
    assert safety.text_problem("a child", {"prompt": "wearing a bikini"}) == safety.REFUSED
    assert safety.text_problem(None, 5, "a fox") == ""


def test_a_saved_characters_own_words_may_not_name_a_child():
    assert safety.character_text_problem("Ada", "tall, auburn hair") == ""
    assert "child" in safety.character_text_problem("Ada", "a little girl")
    assert safety.character_text_problem("Ada", "naked") == safety.REFUSED
