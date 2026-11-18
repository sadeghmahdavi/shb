from pathlib import Path

PCAP_ROOT: Path = Path("data/pcap")

WELL_KNOWN_PORTS: set[int] = {80, 443, 8080, 8443, 21, 22, 25, 53, 110, 143, 993, 995}

HASH_READ_CHUNK_BYTES: int = 1024 * 1024
