# PyPI Release Guide — fastrtc-compact

Scope: **building and publishing to PyPI.** Version numbering and in-repo
changes are covered in `VERSIONING.md` (do that first). Git tagging and GitHub
Releases are covered in the GitHub release guide.

All commands use the `python3 -m <tool>` form so they always run the tool
installed in the **active venv**, never a stale system copy (Ubuntu ships an
ancient twine 3.8.0 at `/usr/bin/twine` that cannot parse modern package
metadata — invoking bare `twine` can silently pick that one up).

Run everything from the project root with the venv active:

```bash
cd ~/PycharmProjects/"FastRTC Source Code"
source .venv/bin/activate
```

---

## Part A — One-time setup (already done; kept for reference / new machines)

### A.1 PyPI account

1. Register at <https://pypi.org/account/register/>
2. Verify the email address.
3. Enable **2FA** (Account settings → Two factor authentication) — mandatory
   for uploading.

### A.2 API token

1. Account settings → **API tokens** → *Add API token*.
2. Scope: select the **fastrtc-compact** project.
   (Only the very first upload of a brand-new project requires an
   account-wide token, because the project doesn't exist yet. After that
   first upload, replace it with a project-scoped token — smaller blast
   radius if it ever leaks.)
3. Copy the token immediately — it is shown exactly once. Format:
   `pypi-AgEIcH...`

### A.3 Store credentials in `~/.pypirc`

The file must be at **`~/.pypirc`** (home directory). twine does not read a
`.pypirc` inside the project folder — if the upload prompts for a token, the
file is in the wrong place or misformatted.

```bash
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-AgEIcH...paste-real-token-here...
EOF
chmod 600 ~/.pypirc
```

Notes:
- `__token__` is a **literal string**, required as-is for API tokens.
- The file lives outside the repo, so it can never be committed. Do not keep
  a copy in the project directory.
- `chmod 600` because it is a plaintext credential.

### A.4 Install/refresh the publishing tools in the venv

```bash
python3 -m pip install -U build twine pkginfo packaging
python3 -m twine --version    # expect 6.x
```

If `python3 -m twine --version` shows anything below 5.x, the venv install
didn't take — rerun the pip line and check for errors.

---

## Part B — Per-release procedure

Precondition: `VERSIONING.md` checklist complete — `pyproject.toml` bumped,
`CHANGES.md` updated, both committed and pushed.

### B.1 Build

```bash
rm -rf dist/
python3 -m build
```

`rm -rf dist/` matters: `dist/*` in later commands globs **everything** in the
folder, and a stale wheel from a previous version would be uploaded alongside
the new one.

Expected final line:
`Successfully built fastrtc_compact-<version>.tar.gz and fastrtc_compact-<version>-py3-none-any.whl`

### B.2 Check metadata

```bash
python3 -m twine check dist/*
```

Both files must report `PASSED`.

Known false alarm: `InvalidDistribution: Metadata is missing required fields:
Name, Version` combined with `supported Metadata-Version: 1.0 ... 2.2` means
an **outdated twine** is running (it cannot parse Metadata-Version 2.4, which
hatchling emits). The package is fine; fix the tool: rerun A.4 and confirm
`python3 -m twine --version` is current.

### B.3 Inspect the artifacts

```bash
# Wheel: only fastrtc/ package files + .dist-info
python3 -m zipfile -l dist/*.whl

# sdist: only backend/, LICENSE, README.md, pyproject.toml, PKG-INFO
tar -tzf dist/*.tar.gz
```

Red flags in the sdist: `demo/`, `docs/`, `test/`, `.idea/`, `justfile`,
`mkdocs.yml` — any of these means the `[tool.hatch.build.targets.sdist]`
exclude list in `pyproject.toml` regressed.

Two files that look like junk but MUST stay in the wheel:
- `fastrtc/speech_to_text/test_file.wav` — used by STT warmup at runtime
- `fastrtc/py.typed` — enables type checking for downstream users

### B.4 Clean-room install test

Never trust a test in the dev venv — it has packages installed that mask
missing dependencies. Use a throwaway venv:

```bash
python3 -m venv /tmp/pubtest
/tmp/pubtest/bin/python3 -m pip install -U pip
/tmp/pubtest/bin/python3 -m pip install dist/*.whl
/tmp/pubtest/bin/python3 -c "import fastrtc; from fastrtc import Stream; print('ok')"
rm -rf /tmp/pubtest
```

While it installs, glance at the dependency list pip resolves — that IS the
declared `dependencies` in action. If `ok` prints, proceed.

### B.5 Upload

```bash
python3 -m twine upload dist/*
```

- Should not prompt (credentials come from `~/.pypirc`; if it prompts, see A.3).
- On success it prints the project URL:
  `https://pypi.org/project/fastrtc-compact/<version>/`

**Point of no return:** a version number can never be re-uploaded, even after
deletion. A broken release is fixed by bumping to the next PATCH version and
uploading that. (A truly harmful release can additionally be *yanked* on the
PyPI web UI — pip then refuses to auto-install it but existing pins keep
working.)

### B.6 Verify the live package

1. Open the PyPI page: README rendered correctly, links in the sidebar
   (Repository / Issues / Documentation) point to the right places.
2. Real-world install test:

```bash
python3 -m venv /tmp/pypitest
/tmp/pypitest/bin/python3 -m pip install fastrtc-compact
/tmp/pypitest/bin/python3 -c "import fastrtc; print(fastrtc.Stream)"
rm -rf /tmp/pypitest
```

(New releases are visible to pip within a minute or two of upload.)

### B.7 Hand off to the GitHub release guide

Tag `v<version>`, push the tag, draft the GitHub Release. The docs header
badge and install instructions take care of themselves from there.

---

## Quick reference (the whole thing in one block)

```bash
cd ~/PycharmProjects/"FastRTC Source Code" && source .venv/bin/activate
rm -rf dist/
python3 -m build
python3 -m twine check dist/*
tar -tzf dist/*.tar.gz
python3 -m venv /tmp/pubtest && /tmp/pubtest/bin/python3 -m pip install dist/*.whl \
  && /tmp/pubtest/bin/python3 -c "import fastrtc; print('ok')" && rm -rf /tmp/pubtest
python3 -m twine upload dist/*
```