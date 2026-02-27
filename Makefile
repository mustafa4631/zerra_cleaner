# Root-level Makefile — delegates to gk-healter/
.PHONY: run clean install uninstall deb rpm appimage

%:
	$(MAKE) -C gk-healter $@
