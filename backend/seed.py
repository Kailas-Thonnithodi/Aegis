from backend import db


def main() -> None:
    claims, policies = db.reset()
    print(f"Loaded {claims} claims and {policies} policies.")


if __name__ == "__main__":
    main()
