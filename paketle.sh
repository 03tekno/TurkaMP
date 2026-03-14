#!/bin/bash

PACKAGE_NAME="turkamp"
VERSION="1.0"
BUILD_DIR="${PACKAGE_NAME}_${VERSION}"

echo "Paketleme süreci başlatılıyor..."

rm -rf "$BUILD_DIR"

# Dizin yapısını oluştur
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$BUILD_DIR/opt/turkamp"

# Dosyaları kopyala
cp turkamp.py "$BUILD_DIR/opt/turkamp/"
cp turkamp.png "$BUILD_DIR/opt/turkamp/"
cp turkamp.png "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"

# Control dosyası
cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: $PACKAGE_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-pyqt6, python3-pyqt6.qtmultimedia
Maintainer: mobilturka <https://github.com/03tekno/>
Description: Turka Music Player
EOF

# Başlatıcı script (/usr/bin/turkamp)
cat <<EOF > "$BUILD_DIR/usr/bin/turkamp"
#!/bin/bash
cd /opt/turkamp
python3 turkamp.py
EOF
chmod +x "$BUILD_DIR/usr/bin/turkamp"

# Desktop dosyası
cat <<EOF > "$BUILD_DIR/usr/share/applications/turkamp.desktop"
[Desktop Entry]
Name=TurkaMP
Exec=/usr/bin/turkamp
Icon=turkamp
Type=Application
Categories=AudioVideo;Audio;Player;GTK;
EOF

dpkg-deb --root-owner-group --build "$BUILD_DIR"

echo "İşlem tamamlandı! $BUILD_DIR.deb dosyası oluşturuldu."