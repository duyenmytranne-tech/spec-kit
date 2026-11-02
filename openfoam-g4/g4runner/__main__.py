import sys

from .cli import main

sys.dont_write_bytecode = True
raise SystemExit(main())
