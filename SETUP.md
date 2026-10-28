# Install the profile

This profile is configured for **`amansanoj/.github`**, with `main` as its default branch. GitHub renders `profile/README.md` directly onto the public user profile at `https://github.com/amansanoj`.

## Repository structure

- `profile/README.md` & `README.md` — public profile README rendered on GitHub.
- `assets/` — animated and theme-aware SVG artwork.
- `data/` — snapshot of public GitHub contributions.
- `scripts/build_profile.py` — standard-library Python generator for profile SVGs.
- `.github/workflows/refresh-profile.yml` — daily GitHub Action to refresh contribution artwork.
- `tests/` — unit tests for calendar parsing and SVG safety.

## Refresh the artwork

The initial SVGs already contain real public contribution data, retrieved on 2026-10-28. The README works immediately without any secrets or external widget servers.

Once published, **Actions → Refresh profile artwork → Run workflow** performs the first online check. The workflow then runs daily at 05:23 UTC / 09:23 Dubai time, subject to GitHub scheduling delays. GitHub may disable scheduled workflows in public repositories after 60 days of inactivity; re-enable the workflow if needed. Repository rules must permit the workflow's bot to write to `main`.

No personal access token is required. The script reads GitHub's public contribution HTML; the workflow uses its built-in token only to commit generated files to this repository. It never reads private repositories. If GitHub changes its HTML or a fetch fails, the script exits with an error instead of replacing the graphic with invented or empty data. The previous committed snapshot remains available, with its date visible.

```sh
# Python 3.10+; standard library only
python3 scripts/build_profile.py --fetch

# Re-render the saved data, offline
python3 scripts/build_profile.py

# Parser and SVG checks
python3 -m unittest discover -s tests -v
```

## Design and editing

- Edit profile text and links in `README.md`.
- Edit layout, wording, and colors in `scripts/build_profile.py`, then run it again.
- Keep all four SVGs: `<picture>` chooses the appropriate light/dark asset.
- Motion runs once and settles. `prefers-reduced-motion` renders a still version. Static SVG renderers display the finished artwork.
- Images contain no scripts, external fonts, or remote image dependencies. Important project descriptions remain selectable native README text.
- Daily counts and activity shades come from the public calendar. The headline is the sum of the displayed daily counts, not a lifetime total. The line above the grid represents weekly totals on a linear scale.

`profile-preview.html` in the outer package is a self-contained visual preview with theme and motion controls. It approximates GitHub's Markdown typography; GitHub controls the final table spacing and surrounding profile layout. Upload only the files in `amansanoj-profile/` to the repository.

## References

The palette follows [Aman's brand tokens](https://github.com/amansanoj/brand/blob/main/tokens.json). The profile's descriptions were checked against the linked public project READMEs. The drawing and generator are original to this package.

The self-contained SVG and cached-calendar approach was inspired by Avi Vashishta's [animated profile guide](https://www.avivashishta.com/blog/build-animated-github-profile-readme) and [contribution visualization guide](https://www.avivashishta.com/blog/animate-github-contribution-graph-portfolio). This implementation uses standard-library HTML parsing and SVG, not the portfolio article's canvas code.

GitHub's [profile README requirements](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme) and [workflow schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) explain publishing and scheduling behavior.
