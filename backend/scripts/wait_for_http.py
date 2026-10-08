"""Wait for an HTTP endpoint to become available in CI."""
import argparse
import time
from urllib.request import urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()
    for _ in range(args.attempts):
        try:
            with urlopen(args.url, timeout=3) as response:
                if response.status < 500:
                    return 0
        except OSError:
            time.sleep(args.delay)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
