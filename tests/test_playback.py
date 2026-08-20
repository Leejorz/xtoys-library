from core.playback import extract_playback_url_from_html, resolve_playback_url


def test_pixeldrain_direct_playback_url_from_id():
    assert resolve_playback_url("pixeldrain", "AbC123", None) == "https://pixeldrain.com/api/file/AbC123"


def test_extract_hmvmania_source_tag():
    html = '<html><video poster="x.jpg"><source src="https://cdn.example/video.mp4" type="video/mp4"></video></html>'
    assert extract_playback_url_from_html(html, "https://hmvmania.com/video/example/") == "https://cdn.example/video.mp4"


def test_extract_pmvhaven_json_content_url():
    html = '<script type="application/ld+json">{"@type":"VideoObject","contentUrl":"https://cdn.example/movie.webm"}</script>'
    assert extract_playback_url_from_html(html, "https://pmvhaven.com/video/example") == "https://cdn.example/movie.webm"


def test_extract_escaped_player_url():
    html = '<script>var player={"file":"https:\\/\\/cdn.example\\/movie.mp4"};</script>'
    assert extract_playback_url_from_html(html, "https://hmvmania.com/video/example/") == "https://cdn.example/movie.mp4"
