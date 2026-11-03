from src.export_download import PlayerAsset, approved_assets, csv_bytes


def test_export_contains_approved_assets_only() -> None:
    assets = [
        PlayerAsset("a1", "p1", "Moon base", "event-1", "approved"),
        PlayerAsset("a2", "p2", "Unsafe logo", "event-1", "rejected"),
    ]

    selected = approved_assets(assets)

    assert [asset.asset_id for asset in selected] == ["a1"]
    assert b"Moon base" in csv_bytes(assets)
    assert b"Unsafe logo" not in csv_bytes(assets)
