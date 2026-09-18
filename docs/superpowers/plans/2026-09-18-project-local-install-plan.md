# Project-local installation implementation plan

1. Default the installer root to its own project folder and remove the
   application-copy step.
2. Download and verify captioner assets below that project root, reusing valid
   model files and a present engine executable.
3. Launch the project-root launcher, update user-facing text, and confirm no
   public install path refers to AppData.
4. Run PowerShell parsing, Python tests, and whitespace checks.
