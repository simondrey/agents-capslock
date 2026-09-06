#!/usr/bin/env python3
"""Persist MCP, agent guidance, and passive lifecycle hooks. No fixed session data."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import tomllib

START = '<!-- agents-capslock:begin -->'
END = '<!-- agents-capslock:end -->'
TSTART = '# agents-capslock:begin'
TEND = '# agents-capslock:end'


def replace_block(text, start, end, block):
    if start in text:
        if end not in text: raise ValueError('Incomplete Agents CapsLock block')
        return re.sub(re.escape(start)+r'.*?'+re.escape(end), lambda _: block.strip(), text, flags=re.S)
    return text.rstrip() + '\n\n' + block.strip() + '\n'


def write_backup(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() == content: return
        shutil.copy2(path, str(path)+'.backup-agents-capslock-'+str(time.time_ns()))
    temp=path.with_name(path.name+'.agents-capslock.tmp')
    temp.write_text(content); os.chmod(temp, 0o600); temp.replace(path)


def connect(home, plugin):
    server = plugin / 'bin/agents-capslock-mcp'
    cli = plugin / 'bin/attention'
    if not server.is_file() or not cli.is_file(): raise ValueError('Install the plugin first')
    config = home / 'config.toml'
    original = config.read_text() if config.exists() else ''
    parsed = tomllib.loads(original)
    if 'agents_capslock' in parsed.get('mcp_servers', {}) and TSTART not in original:
        raise ValueError('An unmanaged agents_capslock MCP entry already exists; review it before connecting')
    env = ['XDG_RUNTIME_DIR','HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY', 'ATTENTION_OWNER_PID',
           'ATTENTION_TARGET','ATTENTION_SESSION','TMUX','TMUX_PANE','HERDR_ENV','HERDR_PANE_ID',
           'HERDR_SESSION','HERDR_SOCKET_PATH','HERDR_CONFIG_PATH']
    block = f'''{TSTART}
[mcp_servers.agents_capslock]
command = {json.dumps(str(server))}
env_vars = {json.dumps(env)}
enabled = true
startup_timeout_sec = 10
tool_timeout_sec = 10
enabled_tools = ["request_attention", "clear_attention", "connection_status"]
[mcp_servers.agents_capslock.tools.request_attention]
approval_mode = "approve"
[mcp_servers.agents_capslock.tools.clear_attention]
approval_mode = "approve"
[mcp_servers.agents_capslock.tools.connection_status]
approval_mode = "approve"
{TEND}'''
    updated = replace_block(original,TSTART,TEND,block)
    tomllib.loads(updated)  # Validate before any writes.
    instructions = home / 'AGENTS.override.md'
    if not instructions.exists() or not instructions.read_text().strip(): instructions = home / 'AGENTS.md'
    guidance=(plugin/'integrations/codex-instructions.md').read_text()
    updated_guidance=replace_block(instructions.read_text() if instructions.exists() else '',START,END,guidance)
    hookfile=home/'hooks.json'
    hooks=json.loads(hookfile.read_text()) if hookfile.exists() else {}
    import shlex
    command=shlex.quote(str(cli))+' hook codex'
    for event in ['SessionStart','PermissionRequest','PostToolUse','UserPromptSubmit','Stop','Interrupt','SessionEnd']:
        groups=hooks.setdefault('hooks',{}).setdefault(event,[])
        # Remove only prior versions of our handler; preserve other policies.
        for group in groups:
            group['hooks']=[h for h in group.get('hooks',[]) if not (
                h.get('type')=='command' and h.get('command','').endswith(' hook codex') and
                (h.get('command') == command or any(x in h.get('command','') for x in ('/simondrey.attention/','/simondrey.agents-capslock/','/.local/bin/attention'))))]
        groups[:]=[g for g in groups if g.get('hooks')]
        groups.append({'hooks':[{'type':'command','command':command,'timeout':3}]})
    write_backup(config, updated)
    write_backup(instructions, updated_guidance)
    write_backup(hookfile, json.dumps(hooks,indent=2)+'\n')
    return [config,instructions,hookfile]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codex-home',type=Path,default=Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))))
    p.add_argument('--plugin-dir',type=Path,default=Path.home()/'.config/omarchy/plugins/simondrey.agents-capslock')
    args=p.parse_args()
    try:
        for path in connect(args.codex_home,args.plugin_dir): print('Configured:',path)
        print('Restart Codex to load MCP and instructions. Review the passive hooks using /hooks; their trust is not bypassed.')
    except (OSError,ValueError) as e: sys.exit(str(e))
