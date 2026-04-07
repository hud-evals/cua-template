#!/bin/bash
# Start desktop services via dinit, then run the main command.
set -e

python3 -c "
import sys
from pathlib import Path
from manual_dinit import ServiceLoader, SimpleDinit

loader = ServiceLoader(Path('/etc/dinit.d'))
services = loader.load_all()
engine = SimpleDinit(services)
engine.start('boot')
print('Desktop services started.', file=sys.stderr)
" >&2

sleep 2

exec "$@"
