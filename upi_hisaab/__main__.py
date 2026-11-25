"""Allow `python -m upi_hisaab ...`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
