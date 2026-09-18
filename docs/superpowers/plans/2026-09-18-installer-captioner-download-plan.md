# Installer captioner download implementation plan

1. Add a PowerShell helper that downloads each pinned captioner file to the
   installed application's `models\captioner` directory, skips valid local
   files, and rejects checksum mismatches.
2. Call that helper and the existing captioner-engine installer from the visible
   main installer before launching Studio.
3. Print concise stage headings and completion details in the installer console.
4. Update the README to distinguish automatic captioner installation from the
   separate full YuE2 training Setup, then run static and automated checks.
