# Releasing the CoinFlow desktop app

Builds are made by GitHub Actions (`.github/workflows/desktop.yml`) on macOS (Apple Silicon and
Intel), Windows and Linux. Every build is smoke-tested: the packaged app starts its local server,
loads its pages and exits.

## Making a release

1. Set the new version in `app/version.py` (e.g. `__version__ = '1.1.0'`) and commit it to `main`.
2. Tag that commit and push the tag:
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```
3. The workflow runs the tests, builds every platform and publishes a GitHub Release with the
   files and a `.sha256` checksum for each. The build stops if the tag doesn't match `app/version.py`.

To try a build without releasing, open **Actions > Desktop app > Run workflow**; the files are
attached to the run as artifacts.

Installed apps check `https://github.com/Fernando12filho/coinflow-fullstack/releases/latest`
and show "Update available" when a newer version is published.

## Signing and notarizing the macOS app

Without signing, macOS shows "unidentified developer" the first time the app is opened (the user
can still open it from System Settings > Privacy & Security > Open Anyway). With a paid Apple
Developer Program membership the builds are signed and notarized, so they open normally.

### What you need from Apple

1. Check the membership is active: <https://developer.apple.com/account> > Membership details.
2. **Developer ID Application certificate.** In Xcode (Settings > Accounts > Manage Certificates >
   + > Developer ID Application) or at <https://developer.apple.com/account/resources/certificates>.
   Then in Keychain Access, find "Developer ID Application: Your Name (TEAMID)", right-click >
   Export, save as `.p12` with a password.
3. **App Store Connect API key** for notarization: <https://appstoreconnect.apple.com/access/integrations/api>
   > Team Keys > + (role: Developer). Download the `.p8` file (only possible once) and note the
   Key ID and the Issuer ID shown on that page.

### GitHub secrets

In the repository: **Settings > Secrets and variables > Actions > New repository secret**.

| Secret | Value |
|---|---|
| `APPLE_CERTIFICATE_P12` | The `.p12` file, base64-encoded: `base64 -i certificate.p12 \| pbcopy` |
| `APPLE_CERTIFICATE_PASSWORD` | The password chosen when exporting the `.p12` |
| `APPLE_SIGNING_IDENTITY` | The certificate's full name, e.g. `Developer ID Application: Your Name (TEAMID)` (`security find-identity -v -p codesigning` lists it) |
| `APPLE_API_KEY_ID` | The API key's Key ID |
| `APPLE_API_ISSUER_ID` | The Issuer ID from the API keys page |
| `APPLE_API_KEY_P8` | The `.p8` file, base64-encoded: `base64 -i AuthKey_XXXX.p8 \| pbcopy` |

When `APPLE_CERTIFICATE_P12` is set, the macOS jobs import the certificate into a temporary
keychain, sign the app with the hardened runtime (`packaging/entitlements.plist`), verify the
signature, notarize it with Apple and staple the ticket. When it isn't set, those steps are
skipped and the build is unsigned.

Never commit the `.p12` or `.p8` files.

## Windows and Linux

Both builds are unsigned. Windows SmartScreen may show "Windows protected your PC" on first run
(More info > Run anyway). The Linux build uses GTK/WebKit for its window and is **experimental**:
the build and its smoke test run in CI, but the window itself hasn't been tried on Linux yet.

## Building locally

```bash
pip install -r requirements-desktop.txt
pyinstaller --noconfirm coinflow.spec
dist/CoinFlow.app/Contents/MacOS/CoinFlow --smoke-test   # macOS; Windows: dist\CoinFlow\CoinFlow.exe
```
