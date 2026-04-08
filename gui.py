import sys
import io
import contextlib
import importlib
import traceback
import json
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
        QFileDialog, QTextEdit, QHBoxLayout, QVBoxLayout, QMessageBox
    )
except ModuleNotFoundError:
    sys.exit("✖ PyQt6 is required: pip install PyQt6")

CONFIG_FILE = Path.home() / ".weeklymark_config.json"


class MainWindow(QWidget):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self.setWindowTitle("WeeklyMark")
        self._build_ui()

    def _build_ui(self) -> None:
        self.vault_edit = QLineEdit()
        vault_btn = QPushButton("Browse…", clicked=self._browse_vault)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("(leave empty → vault folder)")
        out_btn = QPushButton("Browse…", clicked=self._browse_output)

        self.summarize_chk = QCheckBox("Add AI Summary")
        self.openai_edit = QLineEdit(echoMode=QLineEdit.EchoMode.Password, placeholderText="OpenAI API key (optional)")

        # Load existing API key if it exists
        cfg = self._load_config()
        if "openai_api_key" in cfg:
            self.openai_edit.setText(cfg["openai_api_key"])

        gen_btn = QPushButton("Generate report", clicked=self._run_cli_main)
        self.log = QTextEdit(readOnly=True, minimumHeight=130)

        layout = QVBoxLayout(self)

        def row(label: str, widget, *extras):
            h = QHBoxLayout();
            h.addWidget(QLabel(label));
            h.addWidget(widget, 1)
            for w in extras: h.addWidget(w)
            layout.addLayout(h)

        row("Vault path:", self.vault_edit, vault_btn)
        row("Output path:", self.output_edit, out_btn)
        layout.addWidget(self.summarize_chk)
        layout.addWidget(self.openai_edit)
        layout.addWidget(gen_btn)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log)

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _browse_vault(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select vault directory")
        self.vault_edit.setText(d or self.vault_edit.text())

    def _browse_output(self) -> None:
        f, _ = QFileDialog.getSaveFileName(self, "Choose output file", "Weekly Report.md", "Markdown (*.md)")
        self.output_edit.setText(f or self.output_edit.text())

    def _run_cli_main(self) -> None:
        # Save API key to config
        cfg = self._load_config()
        if self.openai_edit.text().strip():
            cfg["openai_api_key"] = self.openai_edit.text().strip()
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(cfg, f, indent=4)
            except Exception as exc:
                self.log.append(f"✖ Could not save config: {exc}")

        # Build CLI args
        argv = []
        vpath = self.vault_edit.text().strip()
        if vpath: argv += [vpath]
        opath = self.output_edit.text().strip()
        if opath: argv += ["--output", opath]
        if self.summarize_chk.isChecked(): argv += ["--summarize"]

        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                orig_argv = sys.argv
                sys.argv = ["weeklymark"] + argv
                try:
                    import __main__ as wk_mod
                    wk_mod.cli_main()
                except SystemExit as se:
                    if se.code not in (0, None): print(f"Exited with code {se.code}")
                finally:
                    sys.argv = orig_argv
        except Exception:
            buf.write("\n" + traceback.format_exc())
        finally:
            self.log.append(buf.getvalue() or "✓ Done.")


def main() -> None:
    app = QApplication(sys.argv)
    # Simple dark mode for PyQt
    app.setStyleSheet(
        "QWidget { background: #232629; color: #DDD; font-size: 13px; } QLineEdit, QTextEdit { background: #31363b; border: 1px solid #555; border-radius: 4px; } QPushButton { background: #3b4045; border: 1px solid #666; padding: 4px 10px; }")
    win = MainWindow(app);
    win.resize(500, 350);
    win.show();
    sys.exit(app.exec())


if __name__ == "__main__":
    main()