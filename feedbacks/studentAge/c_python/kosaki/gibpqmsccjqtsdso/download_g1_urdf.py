# -*- coding: utf-8 -*-
"""Download three official Unitree G1 URDF files (Python 2.7 / 3.x)."""
from __future__ import print_function
import os
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

BASE = 'https://raw.githubusercontent.com/unitreerobotics/unitree_ros/master/robots/g1_description/'
FILES = ['g1_23dof_mode_10.urdf', 'g1_29dof_mode_11.urdf', 'g1_29dof_mode_13.urdf']
OUTPUT = 'unitree_g1_urdf'
if not os.path.isdir(OUTPUT):
    os.makedirs(OUTPUT)
for name in FILES:
    dest = os.path.join(OUTPUT, name)
    print('Downloading:', name)
    try:
        raw = urlopen(BASE + name, timeout=25).read()
        if not raw.lstrip().startswith(b'<robot'):
            raise ValueError('Unexpected content; not URDF XML')
        with open(dest, 'wb') as f:
            f.write(raw)
        print('Saved:', dest, len(raw), 'bytes')
    except Exception as ex:
        print('FAILED:', name, ex)
print('Done. Files sourced from official unitreerobotics/unitree_ros.')
