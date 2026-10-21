#!/usr/bin/env python3
import sys
from youtube_hybrid import main
if len(sys.argv) == 1:
    sys.argv += ['collect', '--mode', 'search']
elif sys.argv[1] == 'collect' and '--mode' not in sys.argv:
    sys.argv += ['--mode', 'search']
main()
