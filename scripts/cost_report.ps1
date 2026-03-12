# Hillhorn / DeepSeek API cost report
# Usage: .\scripts\cost_report.ps1 [day|week]

$dataRoot = $env:HILLHORN_DATA_ROOT; if (-not $dataRoot) { $dataRoot = "C:\hillhorn_data" }
$usagePath = Join-Path $dataRoot "deepseek_usage.json"

# Prices per 1M tokens (DeepSeek API, approximate)
$PRICE_INPUT  = 0.14   # $ per 1M input
$PRICE_OUTPUT = 0.28   # $ per 1M output (deepseek-chat)
$PRICE_REASONER_IN  = 0.55
$PRICE_REASONER_OUT = 2.19

$period = if ($args[0]) { $args[0] } else { "day" }

if (-not (Test-Path $usagePath)) {
    Write-Host "Usage file not found: $usagePath" -ForegroundColor Yellow
    Write-Host "Run some agent queries first."
    exit 0
}

$data = Get-Content $usagePath -Raw | ConvertFrom-Json
$dates = $data.PSObject.Properties.Name | Sort-Object -Descending

if ($period -eq "week") {
    $dates = $dates | Select-Object -First 7
} else {
    $dates = $dates | Select-Object -First 1
}

$totalCalls = 0
$totalIn = 0
$totalOut = 0
$byAgent = @{}

foreach ($d in $dates) {
    $day = $data.$d
    foreach ($prop in $day.PSObject.Properties) {
        $agent = $prop.Name
        $e = $prop.Value
        $calls = [int]$e.calls
        $inp = [long]$e.input_tokens
        $out = [long]$e.output_tokens
        $totalCalls += $calls
        $totalIn += $inp
        $totalOut += $out
        if (-not $byAgent[$agent]) {
            $byAgent[$agent] = @{ calls = 0; in = 0; out = 0 }
        }
        $byAgent[$agent].calls += $calls
        $byAgent[$agent].in += $inp
        $byAgent[$agent].out += $out
    }
}

# Reasoner agents: planner, architect, tester_math
$reasonerAgents = @("planner", "architect", "tester_math")
$costChat = ($totalIn / 1e6) * $PRICE_INPUT + ($totalOut / 1e6) * $PRICE_OUTPUT
# Simplified: assume reasoner for planner/architect
$cost = $costChat

Write-Host "=== DeepSeek Usage ($period) ===" -ForegroundColor Cyan
Write-Host "Dates: $($dates -join ', ')"
Write-Host "Total calls: $totalCalls"
Write-Host "Input tokens:  $totalIn"
Write-Host "Output tokens: $totalOut"
Write-Host ""
Write-Host "By agent:" -ForegroundColor Yellow
foreach ($a in $byAgent.Keys | Sort-Object) {
    $v = $byAgent[$a]
    Write-Host "  $a : $($v.calls) calls, in=$($v.in), out=$($v.out)"
}
Write-Host ""
$est = [math]::Round($cost, 4)
Write-Host "Estimated cost: ~`$$est USD" -ForegroundColor Green
Write-Host "(Prices: input `$$PRICE_INPUT/1M, output `$$PRICE_OUTPUT/1M tokens)"
