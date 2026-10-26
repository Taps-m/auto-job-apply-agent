# Background prototype — V 0.6.5

Double-click **Start Background Agent.cmd** in the project folder. It starts
the local dashboard and worker without a terminal or this chat remaining open.
Use **Stop Background Agent.cmd** to stop it. The dashboard Start/Stop worker
buttons still work independently.

Windows must remain signed in, awake, and connected to the internet. This is a
desktop background process, not a cloud service or an offline job portal.
It does not install a scheduled task or automatically start after reboot.

## Scope

- Processes queued Dover employer applications using the installed Edge browser.
- Uploads the CV and fills required fields from saved verified answers.
- Keeps up to three attention pages open to control memory usage.
- Leaves blocked applications in SQLite and continues with the next queued job.
- Reports worker activity across dashboard restarts using a local heartbeat.
- Preserves uncertain attempts without retrying them automatically.
- Uses the existing daily discovery schedule while the local server runs.

**Final submission remains manual in this prototype.** It cannot accept terms,
solve verification challenges, infer missing answers, or apply across all seven
portals. Search results do not automatically become queued applications: open
an application detail and queue its supported employer URL.

Sessions and personal data stay in ignored data/. Logs: background-server.log,
background-error.txt and worker.log. A previously running dashboard is reused
and is not terminated by Stop Background Agent.cmd.

Validation uses isolated local tests; no application is submitted by testing.
