project('gk-healter',
  version: '0.1.1',
  meson_version: '>= 0.59.0',
  default_options: ['warning_level=2'],
)

# ── Directories ──────────────────────────────────────────────────────────────
python  = import('python').find_installation('python3')
gnome   = import('gnome')
i18n    = import('i18n')

prefix  = get_option('prefix')       # /usr
datadir = join_paths(prefix, get_option('datadir'))  # /usr/share
bindir  = join_paths(prefix, get_option('bindir'))   # /usr/bin

app_id  = 'io.github.gkdevelopers.GKHealter'
app_name = meson.project_name()       # gk-healter
pkgdatadir = join_paths(datadir, app_name)

# ── Launcher script ─────────────────────────────────────────────────────────
conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('DATADIR', datadir)
conf.set('APP_VERSION', meson.project_version())

configure_file(
  input: join_paths('src', 'gk-healter.in'),
  output: 'gk-healter',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

# ── Python source files ─────────────────────────────────────────────────────
python_sources = [
  'src/__init__.py',
  'src/main.py',
  'src/ui.py',
  'src/cleaner.py',
  'src/utils.py',
  'src/history_manager.py',
  'src/settings_manager.py',
  'src/auto_maintenance_manager.py',
  'src/i18n_manager.py',
  'src/health_engine.py',
  'src/service_analyzer.py',
  'src/log_analyzer.py',
  'src/disk_analyzer.py',
  'src/recommendation_engine.py',
  'src/ai_engine.py',
  'src/pardus_analyzer.py',
  'src/logger.py',
]

install_data(python_sources, install_dir: join_paths(pkgdatadir, 'src'))

# ── Locale / translation JSON files ─────────────────────────────────────────
locale_files = [
  'src/locale/en.json',
  'src/locale/tr.json',
]

install_data(locale_files, install_dir: join_paths(pkgdatadir, 'src', 'locale'))

# ── UI resources ─────────────────────────────────────────────────────────────
install_data(
  'resources/main_window.ui',
  install_dir: join_paths(pkgdatadir, 'resources'),
)

# ── Polkit policy ────────────────────────────────────────────────────────────
install_data(
  join_paths('data', app_id + '.policy'),
  install_dir: join_paths(datadir, 'polkit-1', 'actions'),
)

# ── Desktop file ─────────────────────────────────────────────────────────────
install_data(
  join_paths('data', app_id + '.desktop'),
  install_dir: join_paths(datadir, 'applications'),
)

# ── AppStream metainfo ───────────────────────────────────────────────────────
install_data(
  join_paths('data', app_id + '.metainfo.xml'),
  install_dir: join_paths(datadir, 'metainfo'),
)

# ── Icons ────────────────────────────────────────────────────────────────────
icon_sizes = ['scalable', '64x64', '128x128', '256x256']

foreach size : icon_sizes
  if size == 'scalable'
    ext = 'svg'
  else
    ext = 'png'
  endif

  icon_file = join_paths('icons', 'hicolor', size, 'apps', app_id + '.' + ext)

  install_data(
    icon_file,
    install_dir: join_paths(datadir, 'icons', 'hicolor', size, 'apps'),
  )
endforeach

# ── Post-install hooks (icon cache, desktop db) ─────────────────────────────
meson.add_install_script('build-aux/meson_post_install.py')
