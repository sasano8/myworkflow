"""Run once locally or from cron; does not install a schedule."""

import argparse
from .application import run, target_date


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument(
        "--date",
        help="Target date YYYY-MM-DD; default: yesterday in the declared timezone",
    )
    args = parser.parse_args(argv)
    try:
        result = run(args.database, args.date or target_date())
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    for message in result.messages:
        print(message.text)
    return result.code


if __name__ == "__main__":
    raise SystemExit(main())
