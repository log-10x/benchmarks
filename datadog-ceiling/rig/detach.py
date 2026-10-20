#!/usr/bin/env python3
"""Start a command in its own session, detached from the launching shell's process group, so
it keeps running if that shell or the agent that started it goes away. The process writes its
PID to <log>.pid and its output to <log>.
  detach.py <log file> <command> [args...]"""
import os, sys

log, cmd = sys.argv[1], sys.argv[2:]
if os.fork():
    os._exit(0)
os.setsid()
if os.fork():
    os._exit(0)
with open(log + '.pid', 'w') as f:
    f.write(str(os.getpid()) + '\n')
out = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
nul = os.open('/dev/null', os.O_RDONLY)
os.dup2(nul, 0); os.dup2(out, 1); os.dup2(out, 2)
os.execvp(cmd[0], cmd)
