import sys
import uuid

from agent import main


def cli(argv: list[str]) -> None:
    for claim_id in argv:
        print(f"{claim_id}: {main.run(claim_id, str(uuid.uuid4()))}")


if __name__ == "__main__":
    cli(sys.argv[1:])
