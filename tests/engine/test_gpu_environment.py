import importlib
import importlib.util

import pytest


@pytest.mark.gpu
def test_gpu_environment_skips_cleanly_without_cuda() -> None:
    if importlib.util.find_spec("torch") is None:
        pytest.skip("torch is not installed")

    torch = importlib.import_module("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA GPU is not available")

    assert torch.cuda.device_count() >= 1
