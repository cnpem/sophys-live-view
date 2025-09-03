# Sophys Live View

Live data visualization interface for usage in Bluesky-based systems.

![Overview of the interface](./images/overview.png)

## 📦 Installation
```sh
micromamba create -f environment.yml
micromamba activate sophys_live_view_env
```


```sh
cd sophys_live_view
pip install .
```

Run your gui

```sh
sophys_live_view ""

```

For development:
```sh
pip install -e ".[dev]"
pre-commit install
```
