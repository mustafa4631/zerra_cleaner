#!/usr/bin/env python3

import os
import subprocess
import shutil

install_prefix = os.environ.get('MESON_INSTALL_PREFIX', '/usr/local')
datadir = os.path.join(install_prefix, 'share')

if not os.environ.get('DESTDIR'):
    if shutil.which('gtk-update-icon-cache'):
        print('Updating icon cache...')
        subprocess.call(['gtk-update-icon-cache', '-qtf', os.path.join(datadir, 'icons', 'hicolor')])

    if shutil.which('update-desktop-database'):
        print('Updating desktop database...')
        subprocess.call(['update-desktop-database', '-q', os.path.join(datadir, 'applications')])
