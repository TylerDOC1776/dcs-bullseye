import uvicorn

from .api import create_app
from .config import load_config
from .store import CommandStore, LogStore, NodeStatusStore


def main():
    config = load_config()
    store = CommandStore(config.data_dir / "commands.json")
    status_store = NodeStatusStore(config.data_dir / "status.json")
    log_store = LogStore(config.data_dir / "log_files", config.data_dir / "logs.json")
    app = create_app(config, store, status_store=status_store, log_store=log_store)
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
