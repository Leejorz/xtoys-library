from core.eroscripts import EroScriptsImporter


def test_short_upload_url_uses_visible_funscript_filename():
    assert EroScriptsImporter._script_link_filename(
        "/uploads/short-url/ABC123",
        "Day 1 - Example.funscript",
    ) == "Day 1 - Example.funscript"


def test_download_attribute_can_supply_funscript_filename():
    assert EroScriptsImporter._script_link_filename(
        "/uploads/short-url/ABC123",
        "",
        "Day 2.funscript",
    ) == "Day 2.funscript"


def test_href_funscript_is_still_supported():
    assert EroScriptsImporter._script_link_filename(
        "/uploads/short-url/example.funscript?download=1",
        "",
    ) == "example.funscript"


def test_non_funscript_link_is_ignored():
    assert EroScriptsImporter._script_link_filename(
        "/uploads/short-url/ABC123",
        "Example.zip",
    ) is None


def test_selected_candidates_remap_blob_urls_by_filename():
    current = [
        ("blob:https://discuss.eroscripts.com/new-1", "One.funscript"),
        ("blob:https://discuss.eroscripts.com/new-2", "Two.funscript"),
    ]
    selected = [
        {"filename": "Two.funscript", "script_url": "blob:https://discuss.eroscripts.com/old-2"}
    ]
    assert EroScriptsImporter._select_current_candidates(current, selected) == [
        ("blob:https://discuss.eroscripts.com/new-2", "Two.funscript")
    ]


def test_selected_candidates_preserve_duplicate_filename_occurrences():
    current = [
        ("https://example.test/a", "Same.funscript"),
        ("https://example.test/b", "Same.funscript"),
    ]
    selected = [{"filename": "Same.funscript"}, {"filename": "Same.funscript"}]
    assert EroScriptsImporter._select_current_candidates(current, selected) == current


def test_blob_download_uses_browser_page_fetch():
    class FakePage:
        def evaluate(self, script, url):
            assert url.startswith("blob:")
            return [123, 34, 97, 99, 116, 105, 111, 110, 115, 34, 58, 91, 93, 125]

    importer = EroScriptsImporter(context=None)
    content = importer.download_script(FakePage(), "blob:https://discuss.eroscripts.com/example")
    assert content == b'{"actions":[]}'


def test_blob_filename_prefers_visible_human_name():
    from core.eroscripts import EroScriptsImporter
    got = EroScriptsImporter._script_link_filename(
        "blob:https://discuss.eroscripts.com/abc",
        "ViciousFox - Tifa's naughty list - filler.funscript",
        "mHV9owS5ihpqDS7zTuA5oYeEWmx.funscript",
        "",
    )
    assert got == "ViciousFox - Tifa's naughty list - filler.funscript"


def test_blob_filename_rejects_generated_download_token_without_human_label():
    from core.eroscripts import EroScriptsImporter
    got = EroScriptsImporter._script_link_filename(
        "blob:https://discuss.eroscripts.com/abc",
        "",
        "mHV9owS5ihpqDS7zTuA5oYeEWmx.funscript",
        "",
    )
    assert got is None


def test_normal_upload_can_still_use_download_attribute():
    from core.eroscripts import EroScriptsImporter
    got = EroScriptsImporter._script_link_filename(
        "/uploads/short-url",
        "",
        "JULIEZ - No Class (Emma Frost PMV).funscript",
        "",
    )
    assert got == "JULIEZ - No Class (Emma Frost PMV).funscript"
