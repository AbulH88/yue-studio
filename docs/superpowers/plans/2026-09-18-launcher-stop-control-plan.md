# Launcher stop control implementation plan

1. Change the public launcher to run the Python server in its own foreground
   command window instead of starting it detached.
2. Use a small background readiness watcher to open the browser only after the
   local endpoint responds, while leaving the foreground window available for
   Ctrl+C.
3. Keep the existing-server path non-destructive: open the browser, explain
   that this launcher does not own that server, and do not attempt to stop it.
4. Verify command references, Python tests, and git whitespace.
