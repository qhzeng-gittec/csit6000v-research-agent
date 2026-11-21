from agent.draft import Draft


def active(text):
    d = Draft()
    d.set(text)
    d.activate()
    return d


def test_refused_before_revision_mode():
    d = Draft()
    ok, msg = d.edit("a", "b")
    assert not ok and "revision mode" in msg
    d.set("abc")
    assert not d.edit("a", "b")[0]  # draft exists but gate has not activated it


def test_exact_unique_replace():
    d = active('He wrote "the mixing weight" here, and nothing else.')
    ok, msg = d.edit("the mixing weight", "a mixing weight")
    assert ok and "exact" in msg
    assert d.text == 'He wrote "a mixing weight" here, and nothing else.' and d.edits == 1


def test_ambiguous_old_rejected_and_draft_untouched():
    d = active("cat and cat")
    ok, msg = d.edit("cat", "dog")
    assert not ok and "2 places" in msg and d.text == "cat and cat" and d.edits == 0


def test_normalised_match_maps_back_to_original_span():
    d = active("Result: “mixing\n  weight” is used.")
    ok, msg = d.edit('"mixing weight"', '"a mixing weight"')
    assert ok and "normalized" in msg
    assert d.text == 'Result: "a mixing weight" is used.'


def test_not_found_gives_nearest_fragment():
    d = active("The router is trained for 3 epochs with lr 2e-4.")
    ok, msg = d.edit("The router is trained for 5 epochs", "x")
    assert not ok and "not found" in msg and "trained for" in msg


def test_too_long_and_empty_old():
    d = active("x" * 400)
    assert "limit" in d.edit("x" * 301, "y")[1]
    assert not d.edit("", "y")[0]
