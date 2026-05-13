# OpenMC Meson Install

This packages allows OpenMC to be pip installable.

**All initial code here was completely vibe coded**

You will need the following packages installed:

```bash
sudo apt-get install -y g++ cmake ninja-build git libhdf5-dev libpng-dev
```

once the dependencies are installed:

```bash
 pip install -v git+https://git@github.com/je-cook/openmc-meson-install.git
```

you can optionally set the version of openmc and other args with

```bash
pip install . \
  --config-settings=setup-args=-Dmpi=true \
  --config-settings=setup-args=-Dopenmp=true \
  --config-settings=setup-args=-Ddagmc=true \
  --config-settings=setup-args=-Dopenmc_revision=0.15.3 \
```

these options have not yet been tested and may require further dependencies installed
