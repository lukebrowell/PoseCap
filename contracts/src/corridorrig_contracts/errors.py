class ContractError(Exception):
    """Base for every wire-format violation raised by this package."""


class FrameDecodeError(ContractError):
    """A wire line could not be decoded into a valid pose frame."""


class JobStatusDecodeError(ContractError):
    """A job status document could not be decoded."""


class SerialDecodeError(ContractError):
    """A serial line could not be parsed into channel values."""
