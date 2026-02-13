# Root-level Makefile — delegates to gk-healter/
.PHONY: run clean install uninstall deb

%:
	$(MAKE) -C gk-healter $@
