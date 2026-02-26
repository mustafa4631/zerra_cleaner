.PHONY: run clean build deb install uninstall

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
	rm -rf dist _build
	rm -f *.deb *.rpm

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
