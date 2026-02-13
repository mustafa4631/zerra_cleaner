.PHONY: run clean build deb

# Configuration
APP_NAME = gk-healter
VERSION = 0.1.0
PYTHON = python3
MAIN_SCRIPT = src/main.py

# Paths
DESTDIR ?= dist
PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
DATADIR ?= $(PREFIX)/share
APPDIR ?= $(DATADIR)/$(APP_NAME)
APPS_DIR ?= $(DATADIR)/applications
ICON_DIR ?= $(DATADIR)/icons/hicolor/scalable/apps

# Development
run:
	@echo "Starting $(APP_NAME) in DEV mode..."
	export PYTHONPATH=.:$$PYTHONPATH && $(PYTHON) $(MAIN_SCRIPT)

clean:
	@echo "Cleaning up..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist
	rm -f *.deb

# Packaging
deb: clean
	@echo "Building Debian package..."
	
	# 1. Create directory structure
	mkdir -p $(DESTDIR)/DEBIAN
	mkdir -p $(DESTDIR)$(APPDIR)/src
	mkdir -p $(DESTDIR)$(APPDIR)/resources
	mkdir -p $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(APPS_DIR)
	mkdir -p $(DESTDIR)$(DATADIR)/pixmaps
	
	# 2. Copy application files
	cp -r src/* $(DESTDIR)$(APPDIR)/src/
	cp -r resources/* $(DESTDIR)$(APPDIR)/resources/
	
	# 3. Copy launcher and desktop file
	cp bin/$(APP_NAME) $(DESTDIR)$(BINDIR)/
	cp $(APP_NAME).desktop $(DESTDIR)$(APPS_DIR)/
	cp resources/gk-healter.png $(DESTDIR)$(DATADIR)/pixmaps/
	
	# 4. Copy Control files
	cp debian/control $(DESTDIR)/DEBIAN/
	cp debian/postinst $(DESTDIR)/DEBIAN/
	cp debian/prerm $(DESTDIR)/DEBIAN/
	
	# 5. Set Permissions
	chmod 755 $(DESTDIR)/DEBIAN/postinst
	chmod 755 $(DESTDIR)/DEBIAN/prerm
	chmod 755 $(DESTDIR)$(BINDIR)/$(APP_NAME)
	find $(DESTDIR)$(APPDIR) -type f -exec chmod 644 {} \;
	find $(DESTDIR)$(APPDIR) -type d -exec chmod 755 {} \;
	
	# 6. Build .deb
	dpkg-deb --build $(DESTDIR) $(APP_NAME)_$(VERSION)_all.deb
	@echo "Package built successfully: $(APP_NAME)_$(VERSION)_all.deb"
