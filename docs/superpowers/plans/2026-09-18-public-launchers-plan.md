# Public launcher implementation plan

1. Replace the old underscore-named batch wrappers with two title-cased,
   double-clickable project-root commands: `Install YuE Studio.cmd` and
   `Launch YuE Studio.cmd`.
2. Make the launch command retain the existing safe startup behavior: reuse a
   running local server, apply a pending safe update, start Python when needed,
   wait for readiness, and open the browser.
3. Update the installer to copy the public launch command into the installed
   app, remove desktop-shortcut creation, launch the installed app automatically
   on successful setup, and show its installed location.
4. Update the README to name only the two public commands, then verify command
   references, automated tests, syntax checks, and git whitespace.
