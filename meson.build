project('openmc-meson-wheel',
      ['cpp'], version: '0.15.3', meson_version: '>=1.3.0', default_options: ['cpp_std=c++17'])

py_mod = import('python')
py = py_mod.find_installation(pure: false)
fs = import('fs')

openmc_src = meson.project_source_root() / 'openmc-src'
ensure_openmc = files('tools/ensure_openmc_source.py')
ensure_result = run_command(
      py,
      ensure_openmc,
      '--source',
      openmc_src,
      '--git-url',
      get_option('openmc_git_url'),
      '--revision',
      get_option('openmc_revision'),
      get_option('allow_fetch') ? '--allow-fetch' : '--no-allow-fetch',
      check: true
)
message(ensure_result.stdout().strip())

if not fs.exists(openmc_src / 'CMakeLists.txt')
  error('OpenMC source tree was not found at ' + openmc_src)
endif

if not fs.exists(openmc_src / 'openmc' / '__init__.py')
  error('OpenMC Python package was not found below ' + openmc_src)
endif

bool_to_onoff = {'true': 'ON', 'false': 'OFF'}

cmake_defs = [
  'OPENMC_USE_MPI=' + bool_to_onoff[get_option('mpi').to_string()],
  'OPENMC_USE_OPENMP=' + bool_to_onoff[get_option('openmp').to_string()],
  'OPENMC_USE_DAGMC=' + bool_to_onoff[get_option('dagmc').to_string()],
  'OPENMC_USE_LIBMESH=' + bool_to_onoff[get_option('libmesh').to_string()],
  'OPENMC_BUILD_TESTS=' + bool_to_onoff[get_option('tests').to_string()],
  'OPENMC_USE_NATIVE_ARCH=' + bool_to_onoff[get_option('optimize_native').to_string()],
  'OPENMC_FORCE_VENDORED_LIBS=' + bool_to_onoff[get_option('force_vendored_libs').to_string()],
  'BUILD_SHARED_LIBS=ON',
  'CMAKE_POSITION_INDEPENDENT_CODE=ON',
  'CMAKE_INSTALL_RPATH=$ORIGIN',
  'CMAKE_BUILD_RPATH=$ORIGIN',
  'CMAKE_BUILD_WITH_INSTALL_RPATH=ON',
  'CMAKE_INSTALL_RPATH_USE_LINK_PATH=ON']

if get_option('hdf5_root') != ''
  cmake_defs += ['HDF5_ROOT=' + get_option('hdf5_root')]
endif

if get_option('openmc_cmake_prefix_path') != ''
  cmake_defs += ['CMAKE_PREFIX_PATH=' + get_option('openmc_cmake_prefix_path')]
endif

cmake_defs += get_option('extra_cmake_args')
cmake_build_dir = meson.current_build_dir() / '_openmc_cmake_build'
cmake_stage_dir = meson.current_build_dir() / '_openmc_cmake_stage'
bundle_arg = get_option('bundle_runtime_deps') ? '--bundle-runtime-deps' : '--no-bundle-runtime-deps'

custom_target('openmc-cmake-artifacts',
  output: [
    'openmc-cmake-build.stamp',
    'openmc_native',
    'libopenmc.so',
    'libfmt.so.11',
    'libpugixml.so.1',
    '_meson_native_manifest.txt',
    '_meson_bundle_manifest.txt'
  ],
  command: [
      py,
      files('tools/meson_cmake_artifacts.py'),
      '--source',
      openmc_src,
      '--build',
      cmake_build_dir,
      '--stage',
      cmake_stage_dir,
      '--buildtype',
      get_option('buildtype'),
      '--generator',
      get_option('openmc_cmake_generator'),
      '--stamp-out',
      '@OUTPUT0@',
      '--native-out',
      '@OUTPUT1@',
      '--lib-out',
      '@OUTPUT2@',
      '--fmt-out',
      '@OUTPUT3@',
      '--pugixml-out',
      '@OUTPUT4@',
      '--manifest-out',
      '@OUTPUT5@',
      '--bundle-manifest-out',
      '@OUTPUT6@',
      bundle_arg,
      '--cmake-defs',
      ','.join(cmake_defs)
  ],
  build_by_default: true,
  build_always_stale: true,
  console: true,
  install: true,
  install_dir: py.get_install_dir(pure: false) / 'openmc' / 'lib',
  install_mode: 'rwxr-xr-x'
)
install_subdir(
    openmc_src / 'openmc',
    install_dir: py.get_install_dir(pure: false),
    strip_directory: false,
    exclude_directories: ['__pycache__'],
    exclude_files: ['*.pyc', '*.pyo']
)
install_data(files('tools/openmc_meson_cli.py'), rename: '_meson_cli.py', install_dir: py.get_install_dir(pure: false) / 'openmc')
