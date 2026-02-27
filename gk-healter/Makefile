.PHONY: run clean build deb rpm appimage install uninstall

# Configuration
APP_NAME = gk-healter
APP_ID = io.github.gkdevelopers.GKHealter
VERSION = 0.1.6
PYTHON = python3
MAIN_SCRIPT = src/main.py

# Paths
DESTDIR ?=
PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
DATADIR ?= $(PREFIX)/share
APPDIR ?= $(DATADIR)/$(APP_NAME)
APPS_DIR ?= $(DATADIR)/applications
METAINFO_DIR ?= $(DATADIR)/metainfo
ICON_BASE ?= $(DATADIR)/icons/hicolor

# Development
run:
	@echo "Starting $(APP_NAME) in DEV mode..."
	export PYTHONPATH=.:$$PYTHONPATH && $(PYTHON) $(MAIN_SCRIPT)

clean:
	@echo "Cleaning up..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist _build rpmbuild
	rm -f *.deb *.rpm *.AppImage appimagetool

# ── Generic install (works on any distro) ────────────────────────────────────
install:
	@echo "Installing $(APP_NAME) to $(DESTDIR)$(PREFIX)..."
	# Application sources
	install -d $(DESTDIR)$(APPDIR)/src/locale
	install -d $(DESTDIR)$(APPDIR)/resources
	install -m 644 src/*.py  $(DESTDIR)$(APPDIR)/src/
	install -m 644 src/locale/*.json $(DESTDIR)$(APPDIR)/src/locale/
	install -m 644 resources/main_window.ui $(DESTDIR)$(APPDIR)/resources/

	# Launcher
	install -d $(DESTDIR)$(BINDIR)
	sed -e 's|@PYTHON@|$(PYTHON)|g' -e 's|@DATADIR@|$(DATADIR)|g' \
	    src/gk-healter.in > $(DESTDIR)$(BINDIR)/$(APP_NAME)
	chmod 755 $(DESTDIR)$(BINDIR)/$(APP_NAME)

	# Desktop file
	install -Dm 644 data/$(APP_ID).desktop $(DESTDIR)$(APPS_DIR)/$(APP_ID).desktop

	# AppStream metainfo
	install -Dm 644 data/$(APP_ID).metainfo.xml $(DESTDIR)$(METAINFO_DIR)/$(APP_ID).metainfo.xml

	# Icons
	install -Dm 644 icons/hicolor/scalable/apps/$(APP_ID).svg  $(DESTDIR)$(ICON_BASE)/scalable/apps/$(APP_ID).svg
	install -Dm 644 icons/hicolor/64x64/apps/$(APP_ID).png     $(DESTDIR)$(ICON_BASE)/64x64/apps/$(APP_ID).png
	install -Dm 644 icons/hicolor/128x128/apps/$(APP_ID).png   $(DESTDIR)$(ICON_BASE)/128x128/apps/$(APP_ID).png
	install -Dm 644 icons/hicolor/256x256/apps/$(APP_ID).png   $(DESTDIR)$(ICON_BASE)/256x256/apps/$(APP_ID).png

	# Refresh caches (skip if DESTDIR is set — packaging scenario)
	@if [ -z "$(DESTDIR)" ]; then \
	    echo "Updating icon cache & desktop database..."; \
	    gtk-update-icon-cache  -qtf $(ICON_BASE) 2>/dev/null || true; \
	    update-desktop-database -q $(APPS_DIR) 2>/dev/null || true; \
	fi

uninstall:
	@echo "Removing $(APP_NAME) from $(DESTDIR)$(PREFIX)..."
	rm -f  $(DESTDIR)$(BINDIR)/$(APP_NAME)
	rm -rf $(DESTDIR)$(APPDIR)
	rm -f  $(DESTDIR)$(APPS_DIR)/$(APP_ID).desktop
	rm -f  $(DESTDIR)$(METAINFO_DIR)/$(APP_ID).metainfo.xml
	rm -f  $(DESTDIR)$(ICON_BASE)/scalable/apps/$(APP_ID).svg
	rm -f  $(DESTDIR)$(ICON_BASE)/64x64/apps/$(APP_ID).png
	rm -f  $(DESTDIR)$(ICON_BASE)/128x128/apps/$(APP_ID).png
	rm -f  $(DESTDIR)$(ICON_BASE)/256x256/apps/$(APP_ID).png
	@if [ -z "$(DESTDIR)" ]; then \
	    gtk-update-icon-cache  -qtf $(ICON_BASE) 2>/dev/null || true; \
	    update-desktop-database -q $(APPS_DIR) 2>/dev/null || true; \
	fi

# ── Debian packaging ────────────────────────────────────────────────────────
deb: clean
	@echo "Building Debian package..."
	
	# 1. Create directory structure
	mkdir -p dist/DEBIAN
	
	# 2. Install into dist/ via the generic target
	$(MAKE) install DESTDIR=dist
	
	# 3. Copy Control files
	# dpkg-deb wants a binary-only control file.  strip the source
	# stanza and write the remaining package stanza directly.
	# note: do NOT copy the original debian/control after running sed
	# as that would undo the filtering.
	sed -n '/^Package:/,$$p' debian/control > dist/DEBIAN/control
	sed -i '1s/^/Version: $(VERSION)\nMaintainer: GK Developers <vastseaoffical0@outlook.com>\n/' dist/DEBIAN/control
	cp debian/postinst dist/DEBIAN/
	cp debian/prerm    dist/DEBIAN/
	
	# 4. Set Permissions
	chmod 755 dist/DEBIAN/postinst
	chmod 755 dist/DEBIAN/prerm
	
	# 5. Build .deb
	fakeroot dpkg-deb --build dist $(APP_NAME)_$(VERSION)_all.deb
	@echo "Package built successfully: $(APP_NAME)_$(VERSION)_all.deb"

# ── RPM packaging ───────────────────────────────────────────────────────────
rpm: clean
	@echo "Building RPM package..."

	# 1. Set up rpmbuild directory structure
	mkdir -p rpmbuild/BUILD rpmbuild/RPMS rpmbuild/SOURCES rpmbuild/SPECS rpmbuild/SRPMS

	# 2. Create source tarball
	mkdir -p rpmbuild/SOURCES/$(APP_NAME)-$(VERSION)
	cp -r src resources data icons debian packaging Makefile meson.build \
	      rpmbuild/SOURCES/$(APP_NAME)-$(VERSION)/
	cp ../LICENSE ../README.md rpmbuild/SOURCES/$(APP_NAME)-$(VERSION)/
	cd rpmbuild/SOURCES && tar czf $(APP_NAME)-$(VERSION).tar.gz $(APP_NAME)-$(VERSION)
	rm -rf rpmbuild/SOURCES/$(APP_NAME)-$(VERSION)

	# 3. Create a simple spec file for direct rpmbuild
	@echo "Name:           $(APP_NAME)"                          >  rpmbuild/SPECS/$(APP_NAME).spec
	@echo "Version:        $(VERSION)"                           >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "Release:        1"                                    >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "Summary:        A lightweight system cleaning utility" >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "License:        MIT"                                  >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "Source0:        $(APP_NAME)-$(VERSION).tar.gz"        >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "BuildArch:      noarch"                               >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo ""                                                     >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%description"                                         >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "GK Healter — professional, lightweight system cleaning utility for Linux." >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo ""                                                     >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%prep"                                                >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%setup -q"                                            >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo ""                                                     >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%install"                                             >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "make install DESTDIR=%{buildroot}"                    >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo ""                                                     >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%files"                                               >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%{_bindir}/$(APP_NAME)"                               >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%{_datadir}/$(APP_NAME)/"                             >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%{_datadir}/applications/$(APP_ID).desktop"           >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%{_datadir}/metainfo/$(APP_ID).metainfo.xml"          >> rpmbuild/SPECS/$(APP_NAME).spec
	@echo "%{_datadir}/icons/hicolor/*/apps/$(APP_ID).*"         >> rpmbuild/SPECS/$(APP_NAME).spec

	# 4. Build RPM
	rpmbuild --define "_topdir $$(pwd)/rpmbuild" -bb rpmbuild/SPECS/$(APP_NAME).spec

	# 5. Copy result
	find rpmbuild/RPMS -name "*.rpm" -exec cp {} . \;
	@echo "RPM package built successfully!"

# ── AppImage packaging ──────────────────────────────────────────────────────
appimage: clean
	@echo "Building AppImage..."

	# 1. Create AppDir structure
	mkdir -p dist/AppDir/usr

	# 2. Install into AppDir
	$(MAKE) install DESTDIR=dist/AppDir

	# 3. Create AppRun script
	@echo '#!/bin/bash'                                          >  dist/AppDir/AppRun
	@echo 'SELF=$$(dirname "$$(readlink -f "$$0")")'             >> dist/AppDir/AppRun
	@echo 'export PATH="$$SELF/usr/bin:$$PATH"'                  >> dist/AppDir/AppRun
	@echo 'export PYTHONPATH="$$SELF/usr/share/$(APP_NAME):$$PYTHONPATH"' >> dist/AppDir/AppRun
	@echo 'export XDG_DATA_DIRS="$$SELF/usr/share:$${XDG_DATA_DIRS:-/usr/share}"' >> dist/AppDir/AppRun
	@echo 'exec python3 "$$SELF/usr/share/$(APP_NAME)/src/main.py" "$$@"' >> dist/AppDir/AppRun
	chmod 755 dist/AppDir/AppRun

	# 4. Copy desktop file and icon to AppDir root
	cp data/$(APP_ID).desktop dist/AppDir/$(APP_ID).desktop
	# Try SVG first, then fallback to PNG
	cp icons/hicolor/256x256/apps/$(APP_ID).png dist/AppDir/$(APP_ID).png 2>/dev/null || \
	cp icons/hicolor/128x128/apps/$(APP_ID).png dist/AppDir/$(APP_ID).png 2>/dev/null || \
	cp icons/hicolor/scalable/apps/$(APP_ID).svg dist/AppDir/$(APP_ID).svg 2>/dev/null || true
	# Also create a .DirIcon
	cp dist/AppDir/$(APP_ID).png dist/AppDir/.DirIcon 2>/dev/null || true

	# 5. Download appimagetool if not present
	@if [ ! -f appimagetool ]; then \
	    echo "Downloading appimagetool..."; \
	    ARCH=$$(uname -m); \
	    wget -q "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$${ARCH}.AppImage" \
	         -O appimagetool; \
	    chmod +x appimagetool; \
	fi

	# 6. Build AppImage
	ARCH=$$(uname -m) ./appimagetool --no-appstream dist/AppDir $(APP_NAME)-$(VERSION)-$$(uname -m).AppImage
	@echo "AppImage built successfully: $(APP_NAME)-$(VERSION)-$$(uname -m).AppImage"
