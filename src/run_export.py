from export_download import InfraiClient, PlayerAsset, export_assets


def main() -> None:
    assets = [
        PlayerAsset("asset-17", "player-4", "Sky temple", "summer-26", "approved"),
        PlayerAsset("asset-18", "player-9", "Blocked decal", "summer-26", "queued"),
    ]
    print(export_assets(InfraiClient(), assets))


if __name__ == "__main__":
    main()
