#!/usr/bin/env python3
"""Merge opt-in passive hook adapters, preserving and backing up existing hooks."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import time
p=argparse.ArgumentParser()
p.add_argument('providers', nargs='+', choices=['codex','grok','cursor'])
args=p.parse_args()
cli=Path.home()/'.local/bin/attention'
if not cli.exists(): p.error('Install Agents CapsLock first')
for provider in args.providers:
    path=Path.home()/({'codex':'.codex/hooks.json','grok':'.grok/hooks/attention.json','cursor':'.cursor/hooks.json'}[provider])
    config=json.loads(path.read_text()) if path.exists() else {}
    if path.exists(): shutil.copy2(path,str(path)+'.backup-attention-'+str(time.time_ns()))
    events={
      'codex':['PermissionRequest','PostToolUse','UserPromptSubmit','Stop','Interrupt','SessionEnd'],
      'grok':['Notification','PostToolUse','PostToolUseFailure','UserPromptSubmit','Stop','StopFailure','StopCancelled','SessionEnd'],
      'cursor':['sessionStart','beforeSubmitPrompt','postToolUse','afterShellExecution','stop']
    }[provider]
    command=shlex.quote(str(cli))+' hook '+provider
    hooks=config.setdefault('hooks',{})
    for event in events:
        handler={'command':command,'timeout':3}
        if provider!='cursor': handler={'hooks':[{'type':'command',**handler}]}
        if event=='Notification': handler['matcher']='permission_prompt|elicitation_dialog'
        existing=hooks.setdefault(event,[])
        if handler not in existing: existing.append(handler)
    if provider=='cursor': config.setdefault('version',1)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(config,indent=2)+'\n')
    print('Installed',path)
    if provider=='codex': print('Review and trust the new hooks in Codex on next launch. No trust bypass is installed.')
    if provider=='cursor': print('Cursor adapter clears calls on lifecycle events; automatic approval-wait detection is not available from its documented hooks.')
