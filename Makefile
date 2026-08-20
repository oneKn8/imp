# A system-wide ROS 2 Humble install puts itself on PYTHONPATH and hijacks imports
# inside the venv, which shows up as a baffling "No module named 'yaml'" from pytest.
# Every target below runs with those variables stripped.
CLEAN_ENV = env -u PYTHONPATH -u AMENT_PREFIX_PATH -u LD_LIBRARY_PATH
PY = $(CLEAN_ENV) .venv/bin/python

.PHONY: setup test prototype0 sweep all

setup:
	uv venv --python 3.10 .venv
	uv pip install --python .venv/bin/python mujoco numpy pytest

test:
	$(PY) -m pytest sim/test_envelope.py -q

prototype0:
	$(PY) sim/run_prototype0.py

sweep:
	$(PY) sim/sweep_margin.py

all: test prototype0
