.PHONY: all help build clean install uninstall

GALAXY=ansible-galaxy
PLAYBOOK=ansible-playbook

COLLECTIONS_HOME=~/.ansible/collections/ansible_collections
COLLECTIONS_ORG=iida
COLLECTIONS_NAME=dnac
COLLECTIONS_VERSION=0.0.1

all: help

help:
	@echo "make command options"
	@echo "  build                 build this collection"
	@echo "  install               install this collection to the users path (~/.ansible/collections)"
	@echo "  uninstall             uninstall this collection from the users path (~/.ansible/collections)"

build: clean
	$(GALAXY) collection build -f

clean:
	rm -rf log/*
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

install: uninstall build
	$(GALAXY) collection install -f $(COLLECTIONS_ORG)-$(COLLECTIONS_NAME)-$(COLLECTIONS_VERSION).tar.gz

uninstall:
	rm -rf $(COLLECTIONS_HOME)/$(COLLECTIONS_ORG)/$(COLLECTIONS_NAME)
