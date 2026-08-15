from app.diagnosis.feature_contract import (
    load_feature_contract,
)


def main() -> None:
    contract = load_feature_contract()

    print(
        "Feature Contract 검증 완료: "
        f"models={contract.model_count}, "
        f"features={contract.total_feature_count}"
    )

    for model in contract.models.values():
        print(
            f"- {model.model_key}: "
            f"{model.feature_count} features"
        )


if __name__ == "__main__":
    main()