from app.services.code_seed import CodeSeedEntry, parse_seed_csv


def test_parse_basic_rows():
    text = "MDAP-001,1,pilot\nMDAP-002,3,cohort b\n"
    entries, errors = parse_seed_csv(text)
    assert errors == []
    assert entries[0] == CodeSeedEntry(code="MDAP-001", max_uses=1, admin_label="pilot")
    assert entries[1] == CodeSeedEntry(code="MDAP-002", max_uses=3, admin_label="cohort b")


def test_parse_skips_comments_and_blanks():
    text = "# code,max_uses,label\n\nMDAP-001,1,pilot\n   \n# trailing comment\n"
    entries, errors = parse_seed_csv(text)
    assert len(entries) == 1
    assert errors == []


def test_parse_defaults_max_uses_and_label():
    entries, errors = parse_seed_csv("MDAP-001\n")
    assert errors == []
    assert entries[0] == CodeSeedEntry(code="MDAP-001", max_uses=1, admin_label=None)


def test_parse_reports_bad_max_uses():
    entries, errors = parse_seed_csv("MDAP-001,notanumber,label\n")
    assert entries == []
    assert len(errors) == 1


def test_parse_keeps_commas_in_label():
    entries, _ = parse_seed_csv("MDAP-001,1,cohort, wave two\n")
    assert entries[0].admin_label == "cohort, wave two"
