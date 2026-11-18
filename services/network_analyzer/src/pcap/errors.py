class NetworkAnalyzerError(RuntimeError):
    """Base error for every deliberate failure inside the network_analyzer pipeline."""


class PcapParseError(NetworkAnalyzerError):
    """Raised when a capture file cannot be read or parsed."""
