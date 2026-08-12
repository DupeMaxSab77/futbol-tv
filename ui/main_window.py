import sys
import threading
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame,
    QLineEdit, QComboBox, QMessageBox, QProgressBar,
    QApplication, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from config import APP_NAME, APP_VERSION, REFRESH_INTERVAL
from utils.api_client import fetch_events, fetch_channels, resolve_stream
from utils.player import MPVPlayer


class Signals(QObject):
    events_loaded = pyqtSignal(list)
    channels_loaded = pyqtSignal(dict)
    stream_resolved = pyqtSignal(str, str)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)


class MatchCard(QFrame):
    """Widget representing a single match."""

    def __init__(self, event: dict, on_play_callback, parent=None):
        super().__init__(parent)
        self.event = event
        self.on_play = on_play_callback
        self.setup_ui()

    def setup_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            MatchCard {
                background-color: #1e293b;
                border-radius: 10px;
                padding: 12px;
                margin: 4px 8px;
            }
            MatchCard:hover {
                background-color: #263548;
            }
        """)
        self.setFixedHeight(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Left: Time + Country flag
        left = QVBoxLayout()

        time_label = QLabel(self.event.get("time", "??:??")[:5])
        time_label.setStyleSheet("color: #38bdf8; font-size: 18px; font-weight: bold;")
        time_label.setFixedWidth(55)
        left.addWidget(time_label)

        country = self.event.get("country", "")
        if country:
            c_label = QLabel(country)
            c_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
            left.addWidget(c_label)

        layout.addLayout(left)

        # Center: Match info
        center = QVBoxLayout()

        desc = self.event.get("description", "Evento")
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        desc_label.setWordWrap(True)
        center.addWidget(desc_label)

        sport = self.event.get("sport", "").capitalize()
        embeds = self.event.get("embeds", [])
        info_text = f"{sport} | {len(embeds)} canal(es) disponible(s)"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #64748b; font-size: 11px;")
        center.addWidget(info_label)

        layout.addLayout(center, 1)

        # Right: Play button
        if embeds:
            btn_layout = QVBoxLayout()

            if len(embeds) == 1:
                play_btn = QPushButton("▶ Ver")
                play_btn.setFixedWidth(80)
                play_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #22c55e;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    QPushButton:hover { background-color: #16a34a; }
                """)
                play_btn.clicked.connect(lambda: self.on_play(self.event, embeds[0]))
                btn_layout.addWidget(play_btn)
            else:
                # Dropdown for multiple channels
                channel_combo = QComboBox()
                channel_combo.setFixedWidth(140)
                channel_combo.setStyleSheet("""
                    QComboBox {
                        background-color: #22c55e;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 10px;
                        font-size: 12px;
                    }
                    QComboBox::drop-down { border: none; }
                    QComboBox QAbstractItemView {
                        background-color: #1e293b;
                        color: white;
                        selection-background-color: #16a34a;
                    }
                """)
                for emb in embeds:
                    channel_combo.addItem(emb.get("name", "Canal"), emb.get("embed_path", ""))

                play_btn = QPushButton("▶ Ver")
                play_btn.setFixedWidth(80)
                play_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #22c55e;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 12px;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    QPushButton:hover { background-color: #16a34a; }
                """)
                play_btn.clicked.connect(lambda: self._play_selected(channel_combo))
                btn_layout.addWidget(channel_combo)
                btn_layout.addWidget(play_btn)

            layout.addLayout(btn_layout)

    def _play_selected(self, combo: QComboBox):
        embed_path = combo.currentData()
        if embed_path:
            for emb in self.event.get("embeds", []):
                if emb.get("embed_path") == embed_path:
                    self.on_play(self.event, emb)
                    break


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.signals = Signals()
        self.player = MPVPlayer()
        self.events = []
        self.channels = {}
        self.current_stream_label = ""

        self.signals.events_loaded.connect(self._on_events_loaded)
        self.signals.channels_loaded.connect(self._on_channels_loaded)
        self.signals.stream_resolved.connect(self._on_stream_resolved)
        self.signals.error.connect(self._on_error)
        self.signals.status_update.connect(self._on_status)

        self.setup_ui()
        self.start_refresh_timer()
        self.refresh_data()

    def setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f172a;
            }
            QLabel {
                color: #e2e8f0;
            }
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e293b;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-bottom: 1px solid #334155;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel(f"⚽ {APP_NAME}")
        title.setStyleSheet("color: #f1f5f9; font-size: 22px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar partido...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.search_input.textChanged.connect(self.filter_events)
        header_layout.addWidget(self.search_input)

        # Refresh button
        refresh_btn = QPushButton("↻ Actualizar")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)

        main_layout.addWidget(header)

        # Status bar
        self.status_label = QLabel("Conectando al servidor...")
        self.status_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 4px 20px;")
        main_layout.addWidget(self.status_label)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.matches_widget = QWidget()
        self.matches_layout = QVBoxLayout(self.matches_widget)
        self.matches_layout.setContentsMargins(10, 10, 10, 10)
        self.matches_layout.setSpacing(4)
        self.matches_layout.addStretch()

        self.scroll_area.setWidget(self.matches_widget)
        content_layout.addWidget(self.scroll_area)

        main_layout.addWidget(content, 1)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(35)
        footer.setStyleSheet("background-color: #1e293b; border-top: 1px solid #334155;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 5, 20, 5)

        self.footer_label = QLabel(f"{APP_NAME} v{APP_VERSION} - Fútbol en vivo")
        self.footer_label.setStyleSheet("color: #64748b; font-size: 10px;")
        footer_layout.addWidget(self.footer_label)
        footer_layout.addStretch()

        self.footer_count = QLabel("")
        self.footer_count.setStyleSheet("color: #64748b; font-size: 10px;")
        footer_layout.addWidget(self.footer_count)

        main_layout.addWidget(footer)

    def start_refresh_timer(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(REFRESH_INTERVAL * 1000)

    def refresh_data(self):
        self.status_label.setText("Actualizando datos...")
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        events = fetch_events()
        channels = fetch_channels()
        self.signals.events_loaded.emit(events)
        self.signals.channels_loaded.emit(channels)

    def _on_events_loaded(self, events: list):
        self.events = events
        self.render_events(events)
        self.footer_count.setText(f"{len(events)} eventos")
        self.status_label.setText(f"Última actualización: {time.strftime('%H:%M:%S')}")

    def _on_channels_loaded(self, channels: dict):
        self.channels = channels

    def render_events(self, events: list):
        # Clear existing cards
        while self.matches_layout.count() > 1:  # Keep the stretch
            item = self.matches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not events:
            empty = QLabel("No hay eventos disponibles")
            empty.setStyleSheet("color: #64748b; font-size: 16px; padding: 40px;")
            empty.setAlignment(Qt.AlignCenter)
            self.matches_layout.insertWidget(0, empty)
            return

        for event in events:
            card = MatchCard(event, self.play_match)
            self.matches_layout.insertWidget(self.matches_layout.count() - 1, card)

    def filter_events(self, text: str):
        if not text:
            self.render_events(self.events)
            return
        text_lower = text.lower()
        filtered = [
            e for e in self.events
            if text_lower in e.get("description", "").lower()
            or text_lower in e.get("sport", "").lower()
            or text_lower in e.get("country", "").lower()
        ]
        self.render_events(filtered)

    def play_match(self, event: dict, embed: dict):
        embed_path = embed.get("embed_path", "")
        if not embed_path:
            QMessageBox.warning(self, "Error", "No hay enlace disponible para este canal.")
            return

        self.current_stream_label = f"{event.get('description', '')} - {embed.get('name', '')}"
        self.status_label.setText(f"Resolviendo stream: {embed.get('name', '')}...")

        threading.Thread(
            target=self._resolve_and_play,
            args=(embed_path,),
            daemon=True
        ).start()

    def _resolve_and_play(self, embed_path: str):
        url = resolve_stream(embed_path)
        if url:
            self.signals.stream_resolved.emit(url, self.current_stream_label)
        else:
            self.signals.error.emit("No se pudo obtener la URL del stream. Intentá con otro canal.")

    def _on_stream_resolved(self, url: str, title: str):
        self.status_label.setText(f"Reproduciendo: {title}")
        try:
            self.player.play(url, title)
        except Exception as e:
            QMessageBox.critical(self, "Error de reproducción", str(e))
            self.status_label.setText("Error al reproducir")

    def _on_error(self, msg: str):
        QMessageBox.warning(self, "Error", msg)
        self.status_label.setText("Error")

    def _on_status(self, msg: str):
        self.status_label.setText(msg)

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
