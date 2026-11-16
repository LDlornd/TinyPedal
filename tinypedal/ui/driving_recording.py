#  TinyPedal is an open-source overlay application for racing simulation.
#  Copyright (C) 2022-2026 TinyPedal developers, see contributors.md file
#
#  This file is part of TinyPedal.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""驾驶数据记录窗口；采样和文件写入由应用级记录器负责。"""

from pathlib import Path

from PySide2.QtCore import QTimer, Qt, QUrl
from PySide2.QtGui import QDesktopServices
from PySide2.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
)

from .. import api, cfg, recorder
from ..constant import CONFIG
from ..i18n import tr
from ._common import BaseDialog, UIScaler, singleton_dialog


@singleton_dialog("driving_recording")
class DrivingRecording(BaseDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.set_utility_title(tr("Driving Data Recorder"))
        self.setMinimumWidth(UIScaler.size(48))
        options = cfg.user.config["driving_recording"]

        self.driver = QLineEdit(api.read.vehicle.driver_name())
        self.driver.setMaxLength(200)
        self.comparison = QLineEdit()
        self.comparison.setMaxLength(200)
        self.folder = QLineEdit(options["last_output_path"])
        self.setup_file = QLineEdit()
        self.notes = QTextEdit()
        self.notes.setAcceptRichText(False)
        self.notes.setMaximumHeight(UIScaler.size(8))
        self.notes.setPlaceholderText(tr("Describe setup changes, tyres, fuel, weather and the handling problem."))
        self.interval = QSpinBox()
        self.interval.setRange(10, 1000)
        self.interval.setSuffix(" ms")
        self.interval.setValue(max(10, min(options["sampling_interval"], 1000)))

        browse_folder = QPushButton(tr("Browse"))
        browse_folder.clicked.connect(self.choose_folder)
        browse_setup = QPushButton(tr("Browse"))
        browse_setup.clicked.connect(self.choose_setup)
        self._edit_controls = (self.driver, self.comparison, self.folder, self.setup_file,
                               self.notes, self.interval, browse_folder, browse_setup)
        form = QFormLayout()
        form.addRow(tr("Driver / nickname"), self.driver)
        form.addRow(tr("Comparison label"), self.comparison)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder)
        folder_layout.addWidget(browse_folder)
        form.addRow(tr("Output folder"), folder_layout)
        setup_layout = QHBoxLayout()
        setup_layout.addWidget(self.setup_file)
        setup_layout.addWidget(browse_setup)
        form.addRow(tr("Optional setup file"), setup_layout)
        form.addRow(tr("Sampling interval"), self.interval)
        form.addRow(tr("Notes"), self.notes)

        self.status_label = QLabel()
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setWordWrap(True)
        self.path_label = QLineEdit()
        self.path_label.setReadOnly(True)
        self.start_button = QPushButton(tr("Start Recording"))
        self.stop_button = QPushButton(tr("Stop Recording"))
        self.zip_button = QPushButton(tr("Export Analysis ZIP"))
        open_button = QPushButton(tr("Open Folder"))
        close_button = QPushButton(tr("Close"))
        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.zip_button.clicked.connect(self.export_zip)
        open_button.clicked.connect(self.open_folder)
        close_button.clicked.connect(self.close)
        buttons = QHBoxLayout()
        for button in (self.start_button, self.stop_button, self.zip_button, open_button, close_button):
            buttons.addWidget(button)
        info = QLabel(tr(
            "Recording starts only when requested. Pauses and missing data are not filled with zeros. "
            "Closing this window or changing the API stops recording."))
        info.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addWidget(self.path_label)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def choose_folder(self):
        selected = QFileDialog.getExistingDirectory(self, tr("Output folder"), self.folder.text())
        if selected:
            self.folder.setText(selected)

    def choose_setup(self):
        selected, _ = QFileDialog.getOpenFileName(
            self, tr("Optional setup file"), "", "Setup (*.set *.svm)")
        if selected:
            self.setup_file.setText(selected)

    def start_recording(self):
        try:
            if not self.folder.text().strip():
                raise ValueError("Please choose an output folder")
            recorder.start(
                api.read, api.name, self.folder.text().strip(), self.driver.text(),
                self.comparison.text(), self.notes.toPlainText(), self.interval.value(),
                self.setup_file.text().strip(), cfg.api.copy())
            options = cfg.user.config["driving_recording"]
            options["last_output_path"] = self.folder.text().strip()
            options["sampling_interval"] = self.interval.value()
            cfg.save(config_type=CONFIG.TYPE_CONFIG)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, tr("Error"), tr(str(error)))
        self.refresh()

    def stop_recording(self):
        recorder.stop()
        self.refresh()

    def export_zip(self):
        folder = recorder.status.folder
        filename, _ = QFileDialog.getSaveFileName(
            self, tr("Export Analysis ZIP"), folder + ".zip", "ZIP (*.zip)")
        if not filename:
            return
        try:
            saved = recorder.export_zip(filename)
            QMessageBox.information(self, tr("Saved"), saved)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, tr("Error"), tr(str(error)))

    def open_folder(self):
        folder = recorder.status.folder or self.folder.text()
        if folder.strip():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(folder).expanduser().resolve())))

    def refresh(self):
        status = recorder.status
        if status.active:
            text = tr("Recording: {0} samples").format(status.samples)
        elif status.folder:
            text = tr("Stopped: {0} samples ({1})").format(status.samples, tr(status.reason))
        else:
            text = tr("Ready to record")
        if status.error:
            text += "\n" + tr("Recording failed. Partial files are kept in the output folder.") + "\n" + status.error
        self.status_label.setText(text)
        self.path_label.setText(status.folder)
        self.start_button.setEnabled(not status.active)
        self.stop_button.setEnabled(status.active)
        self.zip_button.setEnabled(not status.active and status.samples > 0)
        for control in self._edit_controls:
            control.setEnabled(not status.active)

    def reject(self):
        self.close()

    def closeEvent(self, event):
        self.timer.stop()
        recorder.stop("window_closed")
        event.accept()
