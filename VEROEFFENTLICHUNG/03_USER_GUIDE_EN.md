# Tenshi 3.0.2 Beta – User guide (English)

**Tenshi is experimental recovery software for Windows 10/11 (64-bit).** Source devices are accessed read-only by the application; recovered files and images must be saved to a separate physical drive. Reading can still worsen the condition of failing hardware. No recovery result is guaranteed to be complete or correct.

## Install and start

- Installer: run `Tenshi_Setup_3.0.2.exe`.
- Portable: extract `Tenshi_Portable_3.0.2_Win64.zip` and run `Tenshi.exe`. Portable means *no installer*; the application still stores some preferences and logs in the Windows user profile.
- The binaries are currently unsigned. Check the publisher's download source and the published SHA-256 checksum; assess Windows security warnings rather than bypassing them blindly.
- Choose one of six interface languages at the top-right; a light/dark theme is available.

## Select source and inspect partitions

1. Use **Select Image** (`.raw`, `.img`, `.dd`) or select a physical disk / Windows volume.
2. The application automatically switches to **Partitions** and starts a read-only quick scan (initial search area up to 64 MiB plus partition metadata). This is not a full scan.
3. Start the deeper search manually if needed.
4. Double-click a partition row to switch to **Files & Folders** and browse its filesystem.
5. Never format, repair, or otherwise write to the source device. Cancel Windows prompts offering to format it.

## Browse and export

Tenshi supports NTFS, FAT32, exFAT and ext2/3/4, with limited Btrfs/XFS functionality. Advanced search and file-category shortcuts are included. A metadata preflight can show **ready**, **warning** or **blocked**; it does *not* verify original contents. Select files and use the green **Batch Export / Resume** button. New jobs use `Tenshi_Export_<signature>/files/`; older `RecoveryDesk_Export_*` jobs remain compatible. Export only to another physical drive. Check recovered files individually.

Deleted-file recovery is experimental and depends on surviving metadata and data blocks. Compressed, encrypted or sparse NTFS streams may be unsupported; Btrfs/XFS deleted-file hints are not exportable. Export success alone is not proof of intact content.

## Imaging and sessions

**Create / Resume Image** writes an image to a separate target. For confirmed media errors there may be 0–3 optional retries, and a choice between **safe stop** and **fill unreadable areas with zeros and log them**. Zero-filled areas are data loss, not recovery. Interrupted imaging may resume from checkpoints if the source still matches. Consider specialist recovery for failing hardware to reduce reads.

**Analysis Sessions** store an image metadata index, not file contents; session files may contain private names and paths. Press **F1** or **Help** for the built-in offline guide. Logs are normally written under `%LOCALAPPDATA%\Tenshi\Logs`. Review diagnostic data before sharing.

**Before using on valuable data:** first practice with disposable test images, ensure the target is a different physical device, and consult a professional for physically unstable media.
