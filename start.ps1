$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
. "$root\.venv\Scripts\Activate.ps1"
pip install -r requirements.txt
Set-Location frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
