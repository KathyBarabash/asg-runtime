# Release Checklist for ASG-Runtime

This checklist should be followed whenever preparing and publishing a new release.

---

## 1. Prepare your code

- [ ] Make sure all intended changes are committed and pushed to `main`.
- [ ] Ensure CI workflows (tests, builds) are passing.


## 2. Update version

- [ ] Open `pyproject.toml`.
- [ ] Update the `[project] version` field to the new version number, e.g.:

```toml
[project]
name = "asg-runtime"
version = "0.2.0"
```

- [ ] Save and commit the version bump:

```bash
git add pyproject.toml
git commit -m "Bump version to 0.2.0"
```


## 3. Push changes

- [ ] Push the commit to GitHub:

```bash
git push origin main
```


## 4. Tag the release

- [ ] Create a new Git tag corresponding to the version:

```bash
git tag v0.2.0
```

- [ ] Push the tag to GitHub:

```bash
git push origin v0.2.0
```


## 5. Verify GitHub Actions

- [ ] Confirm that:
  - The Docker image is built and pushed successfully.
  - The Python dist package is built and attached to the GitHub Release.


## 6. Final checks

- [ ] Check the newly created Release on GitHub:
  - Title should be the version number (e.g., `v0.2.0`).
  - Artifacts (wheel/tarball) are attached.
- [ ] Optionally edit the Release description to include highlights of the changes.


