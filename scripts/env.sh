# Source this: tool paths for the project (Git Bash)
export KICAD_BIN="/c/Program Files/KiCad/10.0/bin"
export KICAD_CLI="$KICAD_BIN/kicad-cli.exe"
export TOOLS="/c/Users/hecto/Documents/KiCAD_Projects/_tools"
export PY="$TOOLS/.venv/Scripts/python.exe"          # KiCad 3.11 + numpy/scipy/shapely/easyeda2kicad
export KRT="$TOOLS/KiCadRoutingTools"                  # router: $PY $KRT/py_router/route.py in.kicad_pcb out.kicad_pcb
export KHAPPY="/c/Users/hecto/.claude/plugins/cache/kicad-happy/kicad-happy/2.3.1/skills"
