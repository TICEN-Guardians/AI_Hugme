import unittest
from unittest.mock import patch

from app.diagnosis.model import model_warmup
from app.diagnosis.model.model_warmup import (
    ModelPrefetchStatus,
)


class ModelWarmupStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        model_warmup._set_model_prefetch_status(
            ModelPrefetchStatus.PENDING
        )

    def tearDown(self) -> None:
        model_warmup._set_model_prefetch_status(
            ModelPrefetchStatus.PENDING
        )

    def test_run_sets_ready_when_all_models_are_ready(self) -> None:
        with patch.object(
            model_warmup,
            "prefetch_model_files",
            return_value=True,
        ):
            model_warmup._run()

        self.assertEqual(
            model_warmup.get_model_prefetch_status(),
            ModelPrefetchStatus.READY,
        )

    def test_run_sets_failed_when_any_model_fails(self) -> None:
        with patch.object(
            model_warmup,
            "prefetch_model_files",
            return_value=False,
        ):
            model_warmup._run()

        self.assertEqual(
            model_warmup.get_model_prefetch_status(),
            ModelPrefetchStatus.FAILED,
        )

    def test_run_sets_failed_when_prefetch_raises(self) -> None:
        with (
            patch.object(
                model_warmup,
                "prefetch_model_files",
                side_effect=RuntimeError("failure"),
            ),
            patch.object(model_warmup.logger, "exception"),
        ):
            model_warmup._run()

        self.assertEqual(
            model_warmup.get_model_prefetch_status(),
            ModelPrefetchStatus.FAILED,
        )

    def test_disabled_prefetch_sets_disabled_status(self) -> None:
        with patch.object(
            model_warmup,
            "prefetch_enabled",
            return_value=False,
        ):
            model_warmup.start_model_prefetch()

        self.assertEqual(
            model_warmup.get_model_prefetch_status(),
            ModelPrefetchStatus.DISABLED,
        )


if __name__ == "__main__":
    unittest.main()
