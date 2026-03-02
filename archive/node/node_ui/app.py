from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from PySide6 import QtWidgets

from node.node_service.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_COMMAND_DIR,
    DEFAULT_LOG_BUNDLE_DIR,
    VALID_ROLES,
    VALID_TRANSPORTS,
)

MANAGED_KEYS = {
    "node_id",
    "role",
    "vps_endpoint",
    "api_key",
    "api_key_file",
    "api_key_env",
    "command_transport",
    "instances",
    "heartbeat_interval",
    "command_poll_interval",
    "command_queue_dir",
    "log_bundle_dir",
    "log_bundle_max_lines",
}


def load_template() -> Dict[str, Any]:
    example = Path(__file__).resolve().parents[1] / "example_config.json"
    if example.exists():
        return json.loads(example.read_text(encoding="utf-8"))
    return {
        "node_id": "node-1",
        "role": "server",
        "vps_endpoint": "https://hub.example.com",
        "api_key": "",
        "command_transport": "filesystem",
        "instances": [
            {
                "name": "Example Instance",
                "cmd_key": "example",
                "exe_path": "C:/DCS/bin/DCS_server.exe",
                "log_path": "C:/Users/DCS/Saved Games/Logs/dcs.log",
                "missions_dir": "C:/Users/DCS/Saved Games/Missions",
            }
        ],
    }


def read_config(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    template = load_template()
    template.setdefault("heartbeat_interval", 30)
    template.setdefault("command_poll_interval", 5)
    template.setdefault("command_queue_dir", str(DEFAULT_COMMAND_DIR))
    template.setdefault("log_bundle_dir", str(DEFAULT_LOG_BUNDLE_DIR))
    template.setdefault("log_bundle_max_lines", 2000)
    return template


class PathPicker(QtWidgets.QWidget):
    """Small helper widget containing a line edit plus a browse button."""

    def __init__(self, browse_for_directory: bool = True, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.browse_for_directory = browse_for_directory
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QtWidgets.QLineEdit(self)
        self.button = QtWidgets.QPushButton("Browse…", self)
        self.button.clicked.connect(self._browse)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self.button)

    def text(self) -> str:
        return self.line_edit.text().strip()

    def setText(self, value: str) -> None:  # noqa: N802 - Qt API compatibility
        self.line_edit.setText(value or "")

    def _browse(self) -> None:
        if self.browse_for_directory:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", self.text() or str(Path.cwd()))
        else:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", self.text() or str(Path.cwd()))
        if path:
            self.line_edit.setText(path)


class InstancesTab(QtWidgets.QWidget):
    COLUMNS = [
        ("cmd_key", "Command Key"),
        ("name", "Server Name"),
        ("exe_path", "Executable Path"),
        ("log_path", "Log Path"),
        ("missions_dir", "Missions Directory"),
    ]

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels([label for _, label in self.COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        button_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Instance", self)
        self.remove_button = QtWidgets.QPushButton("Remove Selected", self)
        self.add_button.clicked.connect(self.add_empty_row)
        self.remove_button.clicked.connect(self.remove_selected)
        button_row.addStretch(1)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.remove_button)
        layout.addLayout(button_row)

    def load_instances(self, instances: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for instance in instances:
            self.add_instance(instance)

    def add_instance(self, instance: Dict[str, Any] | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        data = instance or {}
        for col, (key, _) in enumerate(self.COLUMNS):
            value = str(data.get(key, "") or "")
            item = QtWidgets.QTableWidgetItem(value)
            if key == "cmd_key":
                item.setText(value.lower())
            self.table.setItem(row, col, item)

    def add_empty_row(self) -> None:
        self.add_instance(
            {
                "cmd_key": "",
                "name": "",
                "exe_path": "",
                "log_path": "",
                "missions_dir": "",
            }
        )

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def collect(self) -> List[Dict[str, Any]]:
        instances: List[Dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            entry: Dict[str, Any] = {}
            for col, (key, _) in enumerate(self.COLUMNS):
                item = self.table.item(row, col)
                entry[key] = (item.text().strip() if item else "").strip()
            if not entry["cmd_key"] or not entry["name"]:
                raise ValueError("All instances must include a command key and server name.")
            if not entry["exe_path"]:
                raise ValueError(f"Instance '{entry['cmd_key']}' missing executable path.")
            if not entry["log_path"]:
                raise ValueError(f"Instance '{entry['cmd_key']}' missing log path.")
            entry["cmd_key"] = entry["cmd_key"].lower()
            if not entry["missions_dir"]:
                entry.pop("missions_dir", None)
            instances.append(entry)
        if not instances:
            raise ValueError("At least one instance is required.")
        return instances


class ConnectionTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QFormLayout(self)
        layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self.node_id_input = QtWidgets.QLineEdit(self)
        self.role_combo = QtWidgets.QComboBox(self)
        for role in sorted(VALID_ROLES):
            self.role_combo.addItem(role.title(), role)

        self.transport_combo = QtWidgets.QComboBox(self)
        for transport in sorted(VALID_TRANSPORTS):
            label = "Filesystem" if transport == "filesystem" else "HTTP (VPS)"
            self.transport_combo.addItem(label, transport)

        self.vps_input = QtWidgets.QLineEdit(self)
        self.api_mode_combo = QtWidgets.QComboBox(self)
        self.api_mode_combo.addItems(["Inline Value", "Key File", "Environment Var"])
        self.api_value_input = QtWidgets.QLineEdit(self)
        self.api_value_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_browse_button = QtWidgets.QPushButton("Browse…", self)
        self.api_browse_button.clicked.connect(self._browse_api_file)
        api_row = QtWidgets.QHBoxLayout()
        api_row.addWidget(self.api_value_input, stretch=1)
        api_row.addWidget(self.api_browse_button)

        self.api_mode_combo.currentIndexChanged.connect(self._sync_api_controls)

        layout.addRow("Node ID", self.node_id_input)
        layout.addRow("Role", self.role_combo)
        layout.addRow("Command Transport", self.transport_combo)
        layout.addRow("VPS Endpoint", self.vps_input)
        layout.addRow("API Credential Type", self.api_mode_combo)
        layout.addRow("API Value / Path", api_row)

    def _sync_api_controls(self) -> None:
        mode = self.api_mode_combo.currentIndex()
        is_file = mode == 1
        self.api_browse_button.setEnabled(is_file)
        self.api_value_input.setEchoMode(QtWidgets.QLineEdit.Normal if mode == 2 else QtWidgets.QLineEdit.Password)

    def _browse_api_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select API Key File", self.api_value_input.text() or "")
        if path:
            self.api_value_input.setText(path)

    def load(self, data: Dict[str, Any]) -> None:
        self.node_id_input.setText(str(data.get("node_id", "")))
        role = str(data.get("role", "")).lower()
        idx = max(0, self.role_combo.findData(role))
        self.role_combo.setCurrentIndex(idx)

        transport = str(data.get("command_transport", "filesystem")).lower()
        t_idx = max(0, self.transport_combo.findData(transport))
        self.transport_combo.setCurrentIndex(t_idx)

        self.vps_input.setText(str(data.get("vps_endpoint", "")))
        if data.get("api_key_file"):
            mode, value = 1, data["api_key_file"]
        elif data.get("api_key_env"):
            mode, value = 2, data["api_key_env"]
        else:
            mode, value = 0, data.get("api_key", "")
        self.api_mode_combo.setCurrentIndex(mode)
        self.api_value_input.setText(str(value or ""))
        self._sync_api_controls()

    def collect(self) -> Dict[str, Any]:
        node_id = self.node_id_input.text().strip()
        if not node_id:
            raise ValueError("Node ID is required.")
        transport = self.transport_combo.currentData()
        payload: Dict[str, Any] = {
            "node_id": node_id,
            "role": self.role_combo.currentData(),
            "command_transport": transport,
            "vps_endpoint": self.vps_input.text().strip(),
        }
        # Reset API keys; mode determines which field we use.
        mode = self.api_mode_combo.currentIndex()
        value = self.api_value_input.text().strip()
        if mode == 0:
            payload["api_key"] = value
            payload["api_key_file"] = None
            payload["api_key_env"] = None
        elif mode == 1:
            if not value:
                raise ValueError("Select a file for the API credential.")
            payload["api_key_file"] = value
            payload["api_key"] = None
            payload["api_key_env"] = None
        else:
            if not value:
                raise ValueError("Provide the environment variable name for the API credential.")
            payload["api_key_env"] = value
            payload["api_key"] = None
            payload["api_key_file"] = None
        if transport == "http" and not payload["vps_endpoint"]:
            raise ValueError("VPS endpoint is required when using HTTP transport.")
        return payload


class PathsTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QFormLayout(self)
        layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self.command_dir_input = PathPicker()
        self.log_dir_input = PathPicker()
        self.log_lines_spin = QtWidgets.QSpinBox(self)
        self.log_lines_spin.setRange(500, 100000)
        self.log_lines_spin.setSingleStep(500)
        self.heartbeat_spin = QtWidgets.QSpinBox(self)
        self.heartbeat_spin.setRange(5, 600)
        self.command_poll_spin = QtWidgets.QSpinBox(self)
        self.command_poll_spin.setRange(1, 120)

        layout.addRow("Command Queue Folder", self.command_dir_input)
        layout.addRow("Log Bundle Folder", self.log_dir_input)
        layout.addRow("Log Bundle Max Lines", self.log_lines_spin)
        layout.addRow("Heartbeat Interval (s)", self.heartbeat_spin)
        layout.addRow("Command Poll Interval (s)", self.command_poll_spin)

    def load(self, data: Dict[str, Any]) -> None:
        self.command_dir_input.setText(str(data.get("command_queue_dir", DEFAULT_COMMAND_DIR)))
        self.log_dir_input.setText(str(data.get("log_bundle_dir", DEFAULT_LOG_BUNDLE_DIR)))
        self.log_lines_spin.setValue(int(data.get("log_bundle_max_lines", 2000)))
        self.heartbeat_spin.setValue(int(data.get("heartbeat_interval", 30)))
        self.command_poll_spin.setValue(int(data.get("command_poll_interval", 5)))

    def collect(self) -> Dict[str, Any]:
        command_dir = self.command_dir_input.text()
        log_dir = self.log_dir_input.text()
        if not command_dir:
            raise ValueError("Command queue directory is required.")
        if not log_dir:
            raise ValueError("Log bundle directory is required.")
        return {
            "command_queue_dir": command_dir,
            "log_bundle_dir": log_dir,
            "log_bundle_max_lines": int(self.log_lines_spin.value()),
            "heartbeat_interval": int(self.heartbeat_spin.value()),
            "command_poll_interval": int(self.command_poll_spin.value()),
        }


class ConfigEditor(QtWidgets.QMainWindow):
    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self.setWindowTitle("DCS Admin Node Config")
        self.resize(800, 600)
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.current_config: Dict[str, Any] = {}

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        path_row = QtWidgets.QHBoxLayout()
        self.config_path_input = QtWidgets.QLineEdit(str(self.config_path))
        self.config_browse_button = QtWidgets.QPushButton("Browse…", self)
        self.config_browse_button.clicked.connect(self._browse_config)
        path_row.addWidget(QtWidgets.QLabel("Config File:"))
        path_row.addWidget(self.config_path_input, stretch=1)
        path_row.addWidget(self.config_browse_button)
        layout.addLayout(path_row)

        self.tabs = QtWidgets.QTabWidget(self)
        self.connection_tab = ConnectionTab()
        self.instances_tab = InstancesTab()
        self.paths_tab = PathsTab()
        self.tabs.addTab(self.connection_tab, "Connection")
        self.tabs.addTab(self.instances_tab, "Instances")
        self.tabs.addTab(self.paths_tab, "Paths")
        layout.addWidget(self.tabs, stretch=1)

        button_row = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton("Reload", self)
        self.save_button = QtWidgets.QPushButton("Save", self)
        self.load_button.clicked.connect(self.load_from_disk)
        self.save_button.clicked.connect(self.save_to_disk)
        button_row.addStretch(1)
        button_row.addWidget(self.load_button)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

        self.status_bar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.load_from_disk()

    def _browse_config(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Select Config File", self.config_path_input.text() or str(self.config_path)
        )
        if path:
            self.config_path_input.setText(path)

    def _update_status(self, message: str, timeout: int = 5000) -> None:
        self.status_bar.showMessage(message, timeout)

    def load_from_disk(self) -> None:
        cfg_path = Path(self.config_path_input.text().strip() or DEFAULT_CONFIG_PATH)
        self.config_path = cfg_path
        data = read_config(cfg_path)
        self.current_config = data
        self.connection_tab.load(data)
        self.instances_tab.load_instances(data.get("instances", []))
        self.paths_tab.load(data)
        self._update_status(f"Loaded config from {cfg_path}")

    def collect_form(self) -> Dict[str, Any]:
        data = {k: v for k, v in self.current_config.items() if k not in MANAGED_KEYS}
        connection = self.connection_tab.collect()
        paths = self.paths_tab.collect()
        instances = self.instances_tab.collect()
        # Clear credential keys before writing whichever is active.
        for key in ("api_key", "api_key_env", "api_key_file"):
            data.pop(key, None)
        data.update(connection)
        data.update(paths)
        data["instances"] = instances
        # Remove blank credential entries
        for key in ("api_key", "api_key_env", "api_key_file"):
            if not data.get(key):
                data.pop(key, None)
        return data

    def save_to_disk(self) -> None:
        try:
            data = self.collect_form()
        except ValueError as err:
            QtWidgets.QMessageBox.warning(self, "Invalid Configuration", str(err))
            return

        cfg_path = Path(self.config_path_input.text().strip() or DEFAULT_CONFIG_PATH)
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.current_config = data
        self._update_status(f"Saved configuration to {cfg_path}")
        QtWidgets.QMessageBox.information(self, "Saved", f"Configuration written to:\n{cfg_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DCS Admin Node configuration editor.")
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional config.json path (defaults to %%ProgramData%%\\DCSAdminNode).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    app = QtWidgets.QApplication(sys.argv)
    config_path = Path(args.config_path) if args.config_path else DEFAULT_CONFIG_PATH
    window = ConfigEditor(config_path=config_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
