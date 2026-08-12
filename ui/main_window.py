import sys
import threading
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame,
    QLineEdit, QComboBox, QMessageBox, QApplication,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QLinearGradient, QPalette

from config import APP_NAME, APP_VERSION, REFRESH_INTERVAL
from utils.api_client import fetch_events, fetch_channels
from utils.player import MPVPlayer


class Signals(QObject):
    events_loaded = pyqtSignal(list)
    channels_loaded = pyqtSignal(dict)
    stream_resolved = pyqtSignal(str, str)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)


STYLE = """
QMainWindow {
    background-color: #0a0e1a;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background: #0a0e1a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QLineEdit {
    background-color: #1a1f35;
    color: #e2e8f0;
    border: 1px solid #2d3654;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: #3b82f6;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
}
QLineEdit::placeholder {
    color: #64748b;
}
QComboBox {
    background-color: #16a34a;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: bold;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #1a1f35;
    color: white;
    border: 1px solid #2d3654;
    selection-background-color: #16a34a;
    border-radius: 6px;
    padding: 4px;
}
"""


class MatchCard(QFrame):
    """Modern match card widget."""

    def __init__(self, event: dict, on_play_callback, parent=None):
        super().__init__(parent)
        self.event = event
        self.on_play = on_play_callback
        self.setup_ui()

    def setup_ui(self):
        self.setFixedHeight(80)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #111827, stop:1 #1a1f35);
                border-radius: 12px;
                border: 1px solid #1e293b;
                padding: 0px;
            }
            QFrame:hover {
                border: 1px solid #334155;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1f35, stop:1 #232b44);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        # Left: Time block
        time_block = QFrame()
        time_block.setFixedSize(60, 50)
        time_block.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 10px;
                border: 1px solid #334155;
            }
        """)
        time_layout = QVBoxLayout(time_block)
        time_layout.setContentsMargins(4, 4, 4, 4)
        time_layout.setAlignment(Qt.AlignCenter)

        time_text = self.event.get("time", "??:??")[:5]
        time_label = QLabel(time_text)
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: 700; background: transparent; border: none;")
        time_layout.addWidget(time_label)

        layout.addWidget(time_block)

        # Center: Match info
        center = QVBoxLayout()
        center.setSpacing(4)

        desc = self.event.get("description", "Evento")
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("""
            color: #f1f5f9;
            font-size: 14px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        desc_label.setWordWrap(True)
        center.addWidget(desc_label)

        # Bottom row: sport + channels count
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        sport = self.event.get("sport", "").capitalize()
        embeds = self.event.get("embeds", [])

        sport_label = QLabel(sport)
        sport_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
            background-color: #1e293b;
            border-radius: 4px;
            padding: 2px 8px;
            border: none;
        """)
        bottom_row.addWidget(sport_label)

        channels_label = QLabel(f"{len(embeds)} canal(es)")
        channels_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
            background-color: #1e293b;
            border-radius: 4px;
            padding: 2px 8px;
            border: none;
        """)
        bottom_row.addWidget(channels_label)
        bottom_row.addStretch()

        center.addLayout(bottom_row)
        layout.addLayout(center, 1)

        # Right: Play button or channel selector
        if embeds:
            right = QVBoxLayout()
            right.setSpacing(4)
            right.setAlignment(Qt.AlignCenter)

            if len(embeds) > 1:
                combo = QComboBox()
                combo.setFixedWidth(130)
                for emb in embeds:
                    combo.addItem(emb.get("name", "Canal"), emb.get("embed_path", ""))
                right.addWidget(combo)
            else:
                combo = None

            play_btn = QPushButton("VER EN VIVO")
            play_btn.setFixedSize(130, 34)
            play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 11px;
                    letter-spacing: 1px;
                }
                QPushButton:hover {
                    background-color: #ef4444;
                }
                QPushButton:pressed {
                    background-color: #b91c1c;
                }
            """)
            play_btn.clicked.connect(lambda: self._play(combo))
            right.addWidget(play_btn, alignment=Qt.AlignCenter)

            layout.addLayout(right)


    def _play(self, combo):
        if combo:
            embed_path = combo.currentData()
        else:
            embeds = self.event.get("embeds", [])
            embed_path = embeds[0].get("embed_path", "") if embeds else ""

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

        self.signals.events_loaded.connect(self._on_events_loaded)
        self.signals.error.connect(self._on_error)
        self.signals.status_update.connect(self._on_status)

        self.setup_ui()
        self.start_refresh_timer()
        self.refresh_data()

    def setup_ui(self):
        self.setWindowTitle(f"{APP_NAME}")
        self.setMinimumSize(700, 550)
        self.resize(850, 650)
        self.setStyleSheet(STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== HEADER =====
        header = QFrame()
        header.setFixedHeight(65)
        header.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border-bottom: 1px solid #1e293b;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        # Logo
        logo = QLabel("⚽ FUTBOLTV")
        logo.setStyleSheet("""
            color: #f1f5f9;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 2px;
            background: transparent;
        """)
        header_layout.addWidget(logo)

        header_layout.addStretch()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar partido, liga, equipo...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self.filter_events)
        header_layout.addWidget(self.search_input)

        # Refresh
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)

        main_layout.addWidget(header)

        # ===== STATUS BAR =====
        self.status_label = QLabel("  Conectando al servidor...")
        self.status_label.setFixedHeight(28)
        self.status_label.setStyleSheet("""
            color: #64748b;
            font-size: 11px;
            background-color: #0f1525;
            border-bottom: 1px solid #1e293b;
            padding-left: 8px;
        """)
        main_layout.addWidget(self.status_label)

        # ===== CONTENT =====
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #0a0e1a;")

        self.matches_widget = QWidget()
        self.matches_widget.setStyleSheet("background-color: #0a0e1a;")
        self.matches_layout = QVBoxLayout(self.matches_widget)
        self.matches_layout.setContentsMargins(20, 16, 20, 16)
        self.matches_layout.setSpacing(8)
        self.matches_layout.addStretch()

        self.scroll_area.setWidget(self.matches_widget)
        main_layout.addWidget(self.scroll_area, 1)

        # ===== FOOTER =====
        footer = QFrame()
        footer.setFixedHeight(32)
        footer.setStyleSheet("background-color: #111827; border-top: 1px solid #1e293b;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 0, 24, 0)

        self.footer_count = QLabel("0 eventos")
        self.footer_count.setStyleSheet("color: #475569; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.footer_count)

        footer_layout.addStretch()

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("color: #475569; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(version_label)

        main_layout.addWidget(footer)

    def start_refresh_timer(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(REFRESH_INTERVAL * 1000)

    def refresh_data(self):
        self.status_label.setText("  Actualizando datos...")
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        events = fetch_events()
        channels = fetch_channels()
        self.signals.events_loaded.emit(events)

    def _on_events_loaded(self, events: list):
        self.events = events
        self.render_events(events)
        self.footer_count.setText(f"{len(events)} eventos")
        self.status_label.setText(f"  Última actualización: {time.strftime('%H:%M:%S')}")

    def render_events(self, events: list):
        while self.matches_layout.count() > 1:
            item = self.matches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not events:
            empty = QLabel("No hay eventos disponibles")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #475569; font-size: 16px; padding: 60px; background: transparent; border: none;")
            self.matches_layout.insertWidget(0, empty)
            return

        for event in events:
            card = MatchCard(event, self.play_match)
            self.matches_layout.insertWidget(self.matches_layout.count() - 1, card)

    def filter_events(self, text: str):
        if not text:
            self.render_events(self.events)
            return
        t = text.lower()
        filtered = [
            e for e in self.events
            if t in e.get("description", "").lower()
            or t in e.get("sport", "").lower()
            or t in e.get("country", "").lower()
        ]
        self.render_events(filtered)

    def play_match(self, event: dict, embed: dict):
        embed_path = embed.get("embed_path", "")
        if not embed_path:
            QMessageBox.warning(self, "Error", "No hay enlace disponible.")
            return

        self.status_label.setText(f"  Resolviendo: {embed.get('name', '')}...")
        label = f"{event.get('description', '')} - {embed.get('name', '')}"

        threading.Thread(
            target=self._resolve_and_play,
            args=(embed_path, label),
            daemon=True
        ).start()

    def _resolve_and_play(self, embed_path: str, label: str):
        from utils.api_client import resolve_stream
        url = resolve_stream(embed_path)
        if url:
            self.signals.stream_resolved.emit(url, label)
        else:
            self.signals.error.emit("No se pudo obtener el stream. Intentá con otro canal.")

    def _on_stream_resolved(self, url: str, title: str):
        self.status_label.setText(f"  Reproduciendo: {title}")
        try:
            self.player.play(url, title)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_label.setText("  Error al reproducir")

    def _on_error(self, msg: str):
        QMessageBox.warning(self, "Error", msg)
        self.status_label.setText("  Error")

    def _on_status(self, msg: str):
        self.status_label.setText(f"  {msg}")

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
