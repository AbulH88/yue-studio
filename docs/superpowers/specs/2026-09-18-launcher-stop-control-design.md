# Launcher stop control design

## Goal

Let a non-technical user stop the local YuE Studio server that their launcher
started.

## Behavior

`Launch YuE Studio.cmd` opens a visible command window titled `YuE Studio
Launcher`. When no server is running, it starts the Python app in that same
window, opens the browser after readiness, and displays `Press Ctrl+C to stop
YuE Studio.` Closing the command window or pressing Ctrl+C stops that server.

When an existing local server is detected, the launcher only opens the browser
and explains that it did not start the existing server, so closing this window
will not stop it.

## Safety and verification

The launcher keeps its Python prerequisite check, pending-update behavior, and
30-second startup error. Verify command syntax and the existing automated test
suite.
