from pathlib import Path

from app.application import Application
from core.eroscripts import EroScriptsImportResult
from core.video_metadata import VideoMetadataExtractor
from storage.database import Database


def test_clean_eroscripts_urls_accepts_multiple_lines_and_dedupes():
    raw = "https://discuss.eroscripts.com/t/one/1\n\nhttps://discuss.eroscripts.com/t/two/2\nhttps://discuss.eroscripts.com/t/one/1\n"
    assert Application._clean_eroscripts_urls(raw) == [
        "https://discuss.eroscripts.com/t/one/1",
        "https://discuss.eroscripts.com/t/two/2",
    ]


def test_video_metadata_extracts_keywords_and_tag_links_without_junk():
    html = '''
    <html><head>
      <meta name="keywords" content="Tifa, Final Fantasy, video, HMV">
      <meta property="article:tag" content="Cosplay">
    </head><body>
      <a rel="tag" href="/tag/animation/">Animation</a>
      <a href="/tags/tifa/">Tifa</a>
      <a href="/category/latest/">Latest</a>
    </body></html>
    '''
    assert VideoMetadataExtractor.extract_tags_from_html(html, "https://example.test/video/1") == [
        "Tifa", "Final Fantasy", "Cosplay", "Animation"
    ]


def test_video_metadata_extracts_jsonld_keywords():
    html = '''<script type="application/ld+json">{
      "@type": "VideoObject",
      "keywords": ["Maka Albarn", "Soul Eater"],
      "genre": "Anime"
    }</script>'''
    tags = VideoMetadataExtractor.extract_tags_from_html(html, "https://example.test/video/1")
    assert tags == ["Maka Albarn", "Soul Eater", "Anime"]


def test_staged_result_reports_file_size(tmp_path):
    staged = tmp_path / "x.funscript"
    staged.write_bytes(b'{"actions":[]}')
    result = EroScriptsImportResult(
        page_url="https://discuss.eroscripts.com/t/x/1",
        script_url="blob:x",
        filename="x.funscript",
        content=b"",
        title="X",
        staged_path=str(staged),
    )
    assert result.file_size == staged.stat().st_size


def test_database_batch_writes_commit_together(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    with db.batch_writes():
        first = db.add_script_metadata("a.funscript", "hash-a")
        second = db.add_script_metadata("b.funscript", "hash-b")
        db.replace_script_tags(first, ["one"])
        db.replace_script_tags(second, ["two"])
    rows = db.connect().execute("SELECT COUNT(*) AS n FROM scripts").fetchone()
    assert rows["n"] == 2
    db.close()


def test_database_batch_writes_rolls_back_on_error(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    try:
        with db.batch_writes():
            db.add_script_metadata("a.funscript", "hash-a")
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    row = db.connect().execute("SELECT COUNT(*) AS n FROM scripts").fetchone()
    assert row["n"] == 0
    db.close()


def test_rule34video_uses_only_explicit_video_tags_row():
    html = '''
    <html><head>
      <meta name="keywords" content="Unrelated Keyword, Another Junk Tag">
    </head><body>
      <a href="/tags/navigation-junk/">Navigation Junk</a>
      <div class="info-row"><span>Categories</span><a href="/categories/3d/">3D</a></div>
      <div class="info-row"><span>Artist</span><a href="/artists/x3d/">X3D</a></div>
      <div class="info-row"><span>Tags</span>
        <a href="/tags/pmv/">pmv</a>
        <a href="/tags/blacked/">blacked</a>
        <a href="/tags/tifa-lockhart-final-fantasy/">tifa lockhart (final fantasy)</a>
        <a href="/tags/big-black-cock/">big black cock</a>
        <a href="/tags/suggest/">+ Suggest</a>
      </div>
      <div class="info-row"><span>Download</span><a href="/download/video.mp4">MP4 1080p</a></div>
      <a href="/tags/recommendation-junk/">Recommendation Junk</a>
    </body></html>
    '''
    assert VideoMetadataExtractor.extract_rule34video_tags(html) == [
        "pmv",
        "blacked",
        "tifa lockhart (final fantasy)",
        "big black cock",
    ]
