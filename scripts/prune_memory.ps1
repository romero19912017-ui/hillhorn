# Hillhorn: prune NWF memory (remove old/low-priority charges)
# Usage: .\scripts\prune_memory.ps1 [max_charges] [max_age_days]

$base = "c:\Hillhorn"
$maxCharges = if ($args[0]) { [int]$args[0] } else { 10000 }
$maxAgeDays = if ($args[1]) { [float]$args[1] } else { 90.0 }

Push-Location $base
try {
    .\venv_hillhorn\Scripts\Activate.ps1
    python -c "
from nwf_memory_utils import prune_field
removed = prune_field(max_charges=$maxCharges, max_age_days=$maxAgeDays)
print(f'Pruned: {removed} charges removed')
"
} finally {
    Pop-Location
}
