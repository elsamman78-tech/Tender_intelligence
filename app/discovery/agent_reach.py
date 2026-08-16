import shutil
import subprocess
from dataclasses import dataclass
from ..config import AGENT_REACH_ENABLED

@dataclass
class AgentReachStatus:
    installed: bool
    enabled: bool
    ok: bool
    output: str


def doctor(timeout: int = 20) -> AgentReachStatus:
    if not AGENT_REACH_ENABLED:
        return AgentReachStatus(False, False, False, 'Disabled by configuration')
    exe = shutil.which('agent-reach')
    if not exe:
        return AgentReachStatus(False, True, False, 'agent-reach CLI not installed; core system remains operational')
    try:
        p = subprocess.run([exe, 'doctor'], capture_output=True, text=True, timeout=timeout, shell=False)
        output = (p.stdout + '\n' + p.stderr).strip()
        return AgentReachStatus(True, True, p.returncode == 0, output[-5000:])
    except Exception as e:
        return AgentReachStatus(True, True, False, str(e))
