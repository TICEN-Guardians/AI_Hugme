from collections import Counter

from app.diagnosis.feature_contract import (
    load_feature_contract,
)
from app.diagnosis.feature_sources import (
    FeatureSource,
    get_feature_source,
)


def main() -> None:
    contract = load_feature_contract()
    source_counts: Counter[FeatureSource] = Counter()
    unresolved_features: set[str] = set()

    for model in contract.models.values():
        for feature_name in model.features:
            source = get_feature_source(feature_name)
            source_counts[source] += 1

            if source == FeatureSource.UNRESOLVED:
                unresolved_features.add(feature_name)

    print("Feature 원천 검증 완료")

    for source, count in sorted(
        source_counts.items(),
        key=lambda item: item[0].value,
    ):
        print(f"- {source.value}: {count}")

    if unresolved_features:
        print("- 미분류 Feature")

        for feature_name in sorted(unresolved_features):
            print(f"  - {feature_name}")

        raise ValueError(
            "Feature 원천 미분류 존재"
        )

    print(
        "전체 Feature 원천 매핑 완료: "
        f"{sum(source_counts.values())}"
    )


if __name__ == "__main__":
    main()