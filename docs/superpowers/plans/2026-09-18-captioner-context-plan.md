# Captioner context capacity implementation plan

1. Change the local ACE-Step server startup argument from 4,096 to 8,192
   context tokens.
2. Add a focused test assertion for the server launch arguments so the smaller
   limit is not accidentally restored.
3. Run Python syntax and tests, then document the required installer refresh
   for an existing local installation.
