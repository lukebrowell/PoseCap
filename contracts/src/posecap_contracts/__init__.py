"""Wire formats shared by every PoseCap process. Stdlib only — by contract."""

from .codec import decode_pose_frame, encode_pose_frame
from .errors import ContractError, FrameDecodeError, JobStatusDecodeError
from .frames import (
    NUM_BETAS,
    NUM_BODY_JOINTS,
    NUM_EXPRESSION,
    NUM_HAND_JOINTS,
    SCHEMA_VERSION,
    FrameStatus,
    PoseFrame,
    PosePayload,
    Vec3,
)
from .job import JobState, JobStatus, decode_job_status, encode_job_status
from .model_assets import (
    MPI_DOWNLOAD_URL,
    REQUIRED_MODEL_ASSETS,
    ModelAsset,
    MpiDownload,
    PublicDownload,
)

__all__ = [
    "MPI_DOWNLOAD_URL",
    "NUM_BETAS",
    "NUM_BODY_JOINTS",
    "NUM_EXPRESSION",
    "NUM_HAND_JOINTS",
    "REQUIRED_MODEL_ASSETS",
    "SCHEMA_VERSION",
    "ContractError",
    "FrameDecodeError",
    "FrameStatus",
    "JobState",
    "JobStatus",
    "JobStatusDecodeError",
    "ModelAsset",
    "MpiDownload",
    "PoseFrame",
    "PosePayload",
    "PublicDownload",
    "Vec3",
    "decode_pose_frame",
    "decode_job_status",
    "encode_job_status",
    "encode_pose_frame",
]
