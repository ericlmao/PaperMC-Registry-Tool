# Paper Registry Keys

A static GitHub Pages site listing every Minecraft registry key (e.g. `minecraft:diamond_sword`) and tag key (e.g. `#minecraft:swords`) for each Minecraft version, sourced from the [PaperMC/Paper](https://github.com/PaperMC/Paper) generated registry key classes.

Each version's data comes only from its own Paper branch:

| Version | Branch |
|---------|--------|
| 26.2 (latest, default) | `main` |
| 26.1.2 | `ver/26.1.2` |
| 1.21.11 | `ver/1.21.11` |
| 1.21.10 | `ver/1.21.10` |
| 1.21.9 | `ver/1.21.9` |
| 1.21.8 | `ver/1.21.8` |
| 1.21.5 | `ver/1.21.5` |
| 1.21.4 | `ver/1.21.4` |

## Usage

Open the site, pick a version from the dropdown (defaults to the latest, 26.2), and browse or filter keys. Click any key to copy it. Versions are linkable via the URL hash, e.g. `#1.21.9`.

## Updating the data

```
python3 scripts/fetch_data.py
```

This refetches the generated key classes (`paper-api/src/generated/java/io/papermc/paper/registry/keys/**`) from every branch listed in `VERSIONS` at the top of the script and rewrites `data/*.json`. To add a new Minecraft version, add its `(version, branch)` pair to that list and rerun.

Tag descriptions (the entries each vanilla tag contains, per version) come from [misode/mcmeta](https://github.com/misode/mcmeta)'s `<version>-data` git tags, which mirror the vanilla data pack for each Minecraft version.

## Deploying to GitHub Pages

1. Push this repo to GitHub.
2. Repo Settings → Pages → Source: "Deploy from a branch", branch `main`, folder `/ (root)`.

## Local preview

```
python3 -m http.server 8000
```

Then open http://localhost:8000 (a server is needed because the site fetches the JSON data files).
