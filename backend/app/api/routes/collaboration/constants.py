"""Collaboration constants — contract feed catalog and presets."""

from app.schemas.collaboration import ContractFeedCatalogItem, ContractFeedPresetItem

CONTRACT_FEED_CATALOG: dict[int, ContractFeedCatalogItem] = {
    1001: ContractFeedCatalogItem(
        id=1001,
        name="SAM.gov Federal Opportunities",
        source="sam.gov",
        description="Federal solicitations and notices from SAM.gov.",
    ),
    1002: ContractFeedCatalogItem(
        id=1002,
        name="GSA eBuy RFQs",
        source="gsa-ebuy",
        description="Task-order RFQs available through GSA eBuy contract vehicles.",
    ),
    1003: ContractFeedCatalogItem(
        id=1003,
        name="NASA SEWP V",
        source="sewp",
        description="IT procurement opportunities from NASA SEWP V.",
    ),
    1004: ContractFeedCatalogItem(
        id=1004,
        name="FPDS Awards Feed",
        source="fpds",
        description="Federal contract awards and modifications from FPDS.",
    ),
    1005: ContractFeedCatalogItem(
        id=1005,
        name="USAspending Awards & Spending",
        source="usaspending",
        description="Agency spending and award intelligence from USAspending.",
    ),
}

CONTRACT_FEED_PRESETS: dict[str, ContractFeedPresetItem] = {
    "federal_core": ContractFeedPresetItem(
        key="federal_core",
        name="Federal Core",
        description="Core federal opportunity feeds for active capture teams.",
        feed_ids=[1001, 1002, 1003],
    ),
    "awards_intel": ContractFeedPresetItem(
        key="awards_intel",
        name="Awards Intelligence",
        description="Award and spending intelligence feeds for partner strategy.",
        feed_ids=[1004, 1005],
    ),
    "full_spectrum": ContractFeedPresetItem(
        key="full_spectrum",
        name="Full Spectrum",
        description="All available contract feeds for broad collaboration access.",
        feed_ids=[1001, 1002, 1003, 1004, 1005],
    ),
}
