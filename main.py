"""Flight Quote Assistant entry point."""
from database import init_db
from ui.app import launch_app


def main():
    init_db()
    launch_app()


if __name__ == "__main__":
    main()
