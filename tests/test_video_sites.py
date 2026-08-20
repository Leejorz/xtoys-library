from app.application import Application
from core.pixeldrain import parse_pixeldrain_url
from builders.index_builder import IndexBuilder


def test_pmvhaven_detection():
    found = Application.detect_video_source(
        "https://pmvhaven.com/video/skinny-girls-2-promo_6a87032ff59b2d6382b61e46?from=home"
    )
    assert found["site"] == "pmvhaven.com"
    assert found["video_id"] == "6a87032ff59b2d6382b61e46"


def test_hmvmania_detection():
    found = Application.detect_video_source(
        "https://hmvmania.com/video/zerozerop-larilaru/#/?playlistId=0&videoId=0"
    )
    assert found["site"] == "hmvmania.com"
    assert found["video_id"] == "zerozerop-larilaru#videoId=0"


def test_pixeldrain_list_parser_preserves_item():
    zero = parse_pixeldrain_url("https://pixeldrain.com/l/kZcixJXJ#item=0")
    one = parse_pixeldrain_url("https://pixeldrain.com/l/kZcixJXJ#item=1")
    assert zero["list_id"] == one["list_id"] == "kZcixJXJ"
    assert zero["item_index"] == 0
    assert one["item_index"] == 1


def test_new_site_index_aliases():
    assert IndexBuilder.normalize_site("pmvhaven.com") == "pmvhaven"
    assert IndexBuilder.normalize_site("hmvmania.com") == "hmvmania"
    assert IndexBuilder.normalize_site("pixeldrain.com") == "pixeldrain"
