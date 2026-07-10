from posecap_contracts import REQUIRED_MODEL_ASSETS, MpiDownload, PublicDownload
from posecap_contracts.model_assets import download_failure_reason

_SMPLX_NPZ = next(
    asset for asset in REQUIRED_MODEL_ASSETS if asset.target_path[-1] == "SMPLX_NEUTRAL_2020.npz"
)


def test_required_assets_cover_the_five_pear_runtime_files() -> None:
    targets = {asset.target_path for asset in REQUIRED_MODEL_ASSETS}
    assert targets == {
        ("assets", "SMPL", "SMPL_NEUTRAL.pkl"),
        ("assets", "SMPLX", "SMPLX_NEUTRAL_2020.npz"),
        ("assets", "SMPLX", "flame_generic_model.pkl"),
        ("assets", "SMPLX", "smpl_mean_params.npz"),
        ("assets", "FLAME", "FLAME2020", "generic_model.pkl"),
    }


def test_mpi_gated_assets_download_with_user_credentials_from_official_domains() -> None:
    mpi_sources = {
        asset.source for asset in REQUIRED_MODEL_ASSETS if isinstance(asset.source, MpiDownload)
    }
    assert {(source.domain, source.sfile) for source in mpi_sources} == {
        ("smpl", "SMPL_python_v.1.1.0.zip"),
        ("smplx", "SMPLX_NEUTRAL_2020.npz"),
        ("flame", "FLAME2020.zip"),
    }
    assert all(source.signup_url.startswith("https://") for source in mpi_sources)


def test_mean_params_is_the_only_public_download_and_is_hash_pinned() -> None:
    public = [asset for asset in REQUIRED_MODEL_ASSETS if isinstance(asset.source, PublicDownload)]
    assert [asset.target_path[-1] for asset in public] == ["smpl_mean_params.npz"]
    assert len(public[0].source.sha256) == 64


def test_html_response_is_reported_as_a_sign_in_problem_not_a_traceback() -> None:
    login_page = b"<!DOCTYPE html><html><body>You must sign in</body></html>"
    reason = download_failure_reason(_SMPLX_NPZ, login_page, len(login_page))
    assert reason is not None
    assert "password" in reason.lower() or "sign in" in reason.lower()
    assert "SMPLX_NEUTRAL_2020.npz" in reason


def test_truncated_download_names_the_expected_file() -> None:
    head = b"PK\x03\x04partial"
    reason = download_failure_reason(_SMPLX_NPZ, head, 12_345)
    assert reason is not None
    assert "SMPLX_NEUTRAL_2020.npz" in reason


def test_wrong_content_names_the_expected_file() -> None:
    head = b"\x00\x00\x00\x00garbage" + b"\x00" * 64
    reason = download_failure_reason(_SMPLX_NPZ, head, _SMPLX_NPZ.min_bytes + 1)
    assert reason is not None
    assert "SMPLX_NEUTRAL_2020.npz" in reason


def test_valid_looking_download_passes_validation() -> None:
    head = b"PK\x03\x04" + b"\x00" * 64
    assert download_failure_reason(_SMPLX_NPZ, head, _SMPLX_NPZ.min_bytes + 1) is None
