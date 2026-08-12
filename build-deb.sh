#!/bin/bash
# Script para construir el paquete .deb
set -e

echo "=== Construyendo paquete FutbolTV ==="

# Check if dpkg-deb is available
if ! command -v dpkg-deb &> /dev/null; then
    echo "Instalando dpkg-deb..."
    apt-get install -y dpkg
fi

# Build directory
BUILD_DIR="/tmp/futbol-tv-build"
APP_DIR="$BUILD_DIR/futbol-tv_1.0.0_all"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/DEBIAN"
mkdir -p "$APP_DIR/opt/futbol-tv"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/share/applications"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy control file
cp debian/control "$APP_DIR/DEBIAN/"

# Copy app files
cp main.py config.py "$APP_DIR/opt/futbol-tv/"
cp -r ui "$APP_DIR/opt/futbol-tv/"
cp -r utils "$APP_DIR/opt/futbol-tv/"
cp -r assets "$APP_DIR/opt/futbol-tv/"

# Create executable
cat > "$APP_DIR/usr/bin/futbol-tv" << 'EOF'
#!/bin/bash
exec python3 /opt/futbol-tv/main.py "$@"
EOF
chmod +x "$APP_DIR/usr/bin/futbol-tv"

# Create desktop entry
cat > "$APP_DIR/usr/share/applications/futbol-tv.desktop" << 'EOF'
[Desktop Entry]
Name=FutbolTV
Comment=Fútbol en vivo
Exec=/usr/bin/futbol-tv
Icon=futbol-tv
Terminal=false
Type=Application
Categories=AudioVideo;Video;TV;
EOF

# Copy icon if exists
if [ -f "assets/icon.png" ]; then
    cp assets/icon.png "$APP_DIR/usr/share/icons/hicolor/256x256/apps/futbol-tv.png"
fi

# Build .deb
dpkg-deb --build "$APP_DIR" "futbol-tv_1.0.0_all.deb"

echo ""
echo "=== Paquete construido ==="
echo "Archivo: futbol-tv_1.0.0_all.deb"
echo ""
echo "Para instalar: sudo dpkg -i futbol-tv_1.0.0_all.deb"
echo "Para desinstalar: sudo dpkg -r futbol-tv"
