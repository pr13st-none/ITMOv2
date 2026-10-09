.PHONY: install test

PYTHON ?= python

install:
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'; print('Standard library only: ready')"

test: install
	@"$(MAKE)" -C demo test PYTHON="$(PYTHON)"
