# Task 0013: End-to-end tutorial — setup.exe install → working stream, with real media

**Status:** in-progress
**Created:** 2026-07-11
**Owner:** alexandremendoncaalvaro
**Execution:** agent (drive real Blender + installer) + HITL (Ale does account/password)
**Spec ref:** doc/specs/0001-live-webcam-pose-streaming.md · supersedes the SVG-mockup guide doc/guides/smplx-model-setup.md

## Context

Ale wants a **complete, guided tutorial suite** proving PoseCap works for a
non-technical user from a **clean machine**: run the Windows installer, onboard,
download the licensed models, convert a Mixamo character, and drive it live from
a video with the preview window — captured as **real media** (screenshots, GIFs,
a demo video), not mockups. A general "install → working" tutorial plus
feature-specific tutorials. Enabling code fixes already landed (below).

## Acceptance Criteria

- [ ] The tutorial STARTS from `setup.exe` — the Inno installer wizard (License →
      Destination → Ready → Installing → Finish), captured. (Ale flagged this as a
      hard requirement; do not skip the installer.)
- [ ] General tutorial `doc/guides/getting-started.md`: clean install → onboarding
      checklist → model setup (download) → Mixamo convert → live test — end to end.
- [ ] Feature tutorials: model setup (replaces `smplx-model-setup.md`, new
      checklist+wizard UI, progress bar), character setup (Mixamo import + Convert),
      live capture (video source + preview + Start Stream + record).
- [ ] Real media: PNG screenshots in `doc/guides/images/`, GIFs of short
      interactions in `doc/media/`, the demo video (`Ale-PoseCAp.mp4`). Each step
      shows the ✓ state + the exact next action (guide, don't make the user guess).
- [ ] HITL end-to-end: models download for real (progress bar), Mixamo `Y Bot.fbx`
      converts, and the stream on `Ale-PoseCAp.mp4` drives the converted armature
      with the preview window visible — money-shot GIF captured.

## Enabling fixes (already landed this session)

- [x] `9f9f51f` task 0012 — Getting Started checklist + guided model-setup dialog.
- [x] `443fbd2` **cookie fix** — the credential download NEVER worked: `download.php`
      sets a session cookie + 302-redirects to the file; urllib dropped the cookie →
      HTML login page. Fixed with `HTTPCookieProcessor` (root-caused live). Also:
      download **progress bar** (`layout.progress`), **Start Stream/Record gated**
      until onboarding complete + hint, ✓/error completion icons.
- [x] `5d054b7` test robustness (session join cap 60s for slow CI). CI green.
- [x] **win.7 installer built** with the fixes: `packaging/dist/PoseCap_v0.1.3-win.7_Windows_Setup.exe`
      (21.8 MB, sha256 DEE03FAFB7D7DD7957593B338DF06F37244DE670DC65029056F4E070CE959AF1;
      cookie fix verified inside the bundled extension zip).

## Plan

- [ ] Uninstall the current PoseCap (clean machine): `%LOCALAPPDATA%\PoseCap\unins000.exe //VERYSILENT`,
      then remove residual `%LOCALAPPDATA%\PoseCap` + the Blender extension
      (`.../Blender/5.0/extensions/user_default/posecap` + vendored `posecap_*`).
- [ ] Install from `PoseCap_v0.1.3-win.7_Windows_Setup.exe`; capture each wizard screen.
- [ ] Blender → onboarding checklist → Set Up wizard → real download (progress bar).
- [ ] Mixamo `Y Bot.fbx` → Target Armature → Convert Character for PoseCap.
- [ ] Source = Video File `Ale-PoseCAp.mp4`, Preview on, Start Stream → capture.
- [ ] Author the `.md` tutorials + assemble media (ffmpeg for GIFs).

## Notes

Append-only. Date each entry.

### 2026-07-11 — Created + enabling fixes landed

Split out of the task 0012 HITL when the end-to-end run exposed the cookie bug.
Fixes above landed + CI green + win.7 built. Full media production handed off to a
fresh session (context budget) — handoff doc carries the machine state, GUI-driving
tips, media asset paths, and the security constraint.

**SECURITY (binding):** the agent must NOT create accounts nor type passwords —
those are Ale's steps (he registers/confirms on the 3 MPI sites and types the
password in the wizard; the agent clicks OK with his per-action permission). Never
put the real password in any tutorial artifact — placeholders only; never film the
password field. Ale's accounts (`ale.corridor@gmail.com`) are registered + confirmed
on SMPL / SMPL-X / FLAME. Registration screenshots (showing the all-3 requirement +
the spam-confirmation gotcha) are at `C:\Users\alexa\Downloads\Register\`.

## Definition of Done

- [ ] All tutorial docs written with real media; the general one runs install→stream.
- [ ] HITL money-shot (stream drives converted Mixamo char + preview) captured.
- [ ] Status → done; Notes closes the task.
