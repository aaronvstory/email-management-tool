from typing import Optional, List, Tuple
import socket

try:
    import dns.resolver  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    dns = None  # type: ignore

COMMON_SIEVE_PORT = 4190


def candidate_endpoints(email_domain: str, imap_host: str) -> List[Tuple[str, int]]:
    hosts: List[Tuple[str, int]] = []
    # SRV discovery if dnspython available
    if dns:
        try:  # pragma: no cover - requires DNS
            for name in [f"_sieve._tcp.{email_domain}", f"_sieve._tcp.{imap_host.split('.',1)[-1]}"]:
                for r in dns.resolver.resolve(name, 'SRV'):
                    hosts.append((str(r.target).rstrip('.'), int(r.port)))
        except Exception:
            pass
    # Direct guesses
    candidates = [
        (imap_host, COMMON_SIEVE_PORT),
        (f"sieve.{email_domain}", COMMON_SIEVE_PORT),
        (f"managesieve.{email_domain}", COMMON_SIEVE_PORT),
        (f"mail.{email_domain}", COMMON_SIEVE_PORT),
    ]
    # Deduplicate, preserve order
    seen = set()
    result: List[Tuple[str, int]] = []
    for h in candidates + hosts:
        if h not in seen:
            seen.add(h)
            result.append(h)
    return result


def tcp_probe(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False
