import hashlib
from pathlib import Path

from configs import HASH_READ_CHUNK_BYTES
from pcap.models import DiscoveredPcap


def discover_pcap_files(root: Path) -> list[DiscoveredPcap]:
    """Walk root/<app>/<scenario>/*.pcap and fingerprint every capture found."""
    discovered: list[DiscoveredPcap] = []
    for app_directory in _list_subdirectories(root):
        for scenario_directory in _list_subdirectories(app_directory):
            for pcap_path in _list_pcap_files(scenario_directory):
                discovered.append(
                    DiscoveredPcap(
                        app_name=app_directory.name,
                        scenario=scenario_directory.name,
                        pcap_path=pcap_path,
                        pcap_hash=compute_pcap_hash(pcap_path),
                    )
                )
    return discovered


def compute_pcap_hash(path: Path) -> str:
    """Return the SHA-256 hash of a capture file's content, read in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _list_subdirectories(path: Path) -> list[Path]:
    """One directory's subdirectories, sorted so discovery order is deterministic."""
    return sorted(p for p in path.iterdir() if p.is_dir())


def _list_pcap_files(path: Path) -> list[Path]:
    """One scenario directory's .pcap files, sorted so discovery order is deterministic."""
    return sorted(path.glob("*.pcap"))
