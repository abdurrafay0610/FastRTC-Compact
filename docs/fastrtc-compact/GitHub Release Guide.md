# GitHub Tag & Release Guide — fastrtc-compact

Scope: **git tags and GitHub Releases.** Version numbering is in
`VERSIONING.md`; building and uploading to PyPI is in `PYPI-RELEASE.md`.
Order per release: VERSIONING checklist → PyPI upload → this guide.

**Repo-specific quirk:** the remote in this clone is named **`github`**, not
`origin`. Every command below uses `github`; copy-pasted commands from the
internet that say `origin` will fail with *"'origin' does not appear to be a
git repository"*. (Optional one-time fix to make the world's copy-paste work:
`git remote rename github origin`.)

---

## 1. Tags vs Releases — know which one you're making

| | Git **tag** | GitHub **Release** |
| --- | --- | --- |
| What it is | A named pointer to one commit, stored in git itself | A GitHub object layered on a tag: title, notes, attached files |
| Created by | `git tag` + `git push` | GitHub web UI or `gh` CLI |
| Who sees it | Anyone cloning the repo | The Releases page, repo sidebar, watchers get notified |
| Powers | Reproducible installs (`...git@v0.0.1`) | Docs header version badge, changelog visibility, "latest release" |

A tag without a Release is invisible to most visitors. A Release cannot exist
without a tag. **Make both, every time.**

Naming convention for this project: **`v` prefix** — `v0.0.1`, `v0.1.0`.
(Upstream's unprefixed tags were deleted; stay consistent from here.)

---

## 2. Per-release procedure

Preconditions: the release commit (version bump + CHANGES.md) is pushed to
`main`, and the PyPI upload succeeded.

### 2.1 Create an annotated tag on the release commit

```bash
git tag -a v0.0.2 -m "Short summary of the release"
```

- `-a` makes an *annotated* tag (has author, date, message) — always use it
  for releases; lightweight tags (no `-a`) are for private bookmarks.
- Run this with the release commit checked out (normally: right after pushing
  it, so `HEAD` is correct). To tag an older commit explicitly:
  `git tag -a v0.0.2 -m "..." <commit-sha>`

### 2.2 Push the tag

```bash
git push github v0.0.2
```

Plain `git push` does **not** push tags — this explicit push is required.
Verify it arrived:

```bash
git ls-remote --tags github
```

### 2.3 Draft the GitHub Release

Web UI (fine at this project's release frequency):

1. Repo → **Releases** → **Draft a new release**
2. *Choose a tag* → select the tag just pushed (do NOT type a new name here —
   that creates a second tag)
3. *Release title*: `v0.0.2`
4. *Description*: paste the `CHANGES.md` entry for this version. Or press
   **"Generate release notes"** for an auto-list of merged PRs/commits and
   edit from there.
5. Optional: attach `dist/fastrtc_compact-0.0.2.tar.gz` and the `.whl` as
   release assets (PyPI is the canonical download; attaching is a courtesy
   mirror, skip if in doubt)
6. Leave *"Set as the latest release"* checked → **Publish release**

CLI alternative (needs `gh auth login` once):

```bash
gh release create v0.0.2 --title "v0.0.2" --notes-file <(sed -n '/^## \[0.0.2\]/,/^## \[/p' CHANGES.md)
# or simply:
gh release create v0.0.2 --title "v0.0.2" --generate-notes
```

### 2.4 What updates automatically after publishing

- **Docs header version badge** — reads the latest Release via the GitHub API.
  Note: results are cached in the browser's sessionStorage, so an
  already-open docs tab keeps showing the old number; a fresh session shows
  the new one.
- **Releases box** on the repo front page.
- **Watchers** who subscribed to releases get a notification.
- Nothing in the repo files needs editing (see VERSIONING.md §1.3).

---

## 3. Fixing mistakes

**Tagged the wrong commit / typo in tag name (not yet pushed):**

```bash
git tag -d v0.0.2         # delete locally, redo
```

**Already pushed:** avoid re-pointing a pushed tag — anyone who fetched it
keeps the old target, and pip's git caching can serve stale code. If the tag
went out wrong:

```bash
git push github --delete v0.0.2   # remove remote tag
git tag -d v0.0.2                 # remove local tag
```

...then decide: if the *release content* was wrong, don't reuse the number —
bump PATCH and release the fixed version (same rule as PyPI). Reusing a tag
name is only acceptable if it was caught within minutes and nobody plausibly
fetched it.

**Release drafted from the wrong tag:** Releases can be edited or deleted
freely on the web UI without touching git — deleting a Release does not
delete its tag (there's a separate checkbox for that).

---

## 4. Per-release checklist

1. [ ] Release commit pushed to `main`; PyPI upload done (PYPI-RELEASE.md)
2. [ ] `git tag -a v<version> -m "<summary>"`
3. [ ] `git push github v<version>`
4. [ ] `git ls-remote --tags github` shows it
5. [ ] Draft Release from the tag, notes from CHANGES.md, Publish
6. [ ] Docs badge shows new version (fresh browser session)

---

## 5. One-time items (state as of 2026-07-14)

- [x] Upstream's 22 inherited tags deleted (local only; they were never on
  the remote)
- [ ] **Draft the Release for the existing `v0.0.1` tag** — tag is pushed,
  Release not yet created. Follow §2.3; notes = the 0.0.1 CHANGES.md entry
  (Gradio removal, librosa/numba → soxr, teardown fixes, ~3x smaller install).
- [ ] Add PyPI badge to README:
  `[![PyPI](https://img.shields.io/pypi/v/fastrtc-compact)](https://pypi.org/project/fastrtc-compact/)`
- [ ] Set repo About → Website to the docs or PyPI URL