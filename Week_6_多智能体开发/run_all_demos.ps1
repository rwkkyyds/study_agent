$ErrorActionPreference = "Stop"

$demoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$section1 = Get-ChildItem -LiteralPath $demoRoot -Directory |
    Where-Object { $_.Name -like "Section_1_*" } |
    Select-Object -First 1
$section2 = Get-ChildItem -LiteralPath $demoRoot -Directory |
    Where-Object { $_.Name -eq "Section_2_LangGraph_HITL" } |
    Select-Object -First 1

if (-not $section1) {
    throw "Cannot find Section_1 demo directory."
}

if (-not $section2) {
    throw "Cannot find Section_2 demo directory."
}

$demos = @(
    (Join-Path $section1.FullName "demo1_parallel_review_workflow.py"),
    (Join-Path $section1.FullName "demo2_conditional_ticket_router.py"),
    (Join-Path $section1.FullName "demo3_subgraph_order_pipeline.py"),
    (Join-Path $section2.FullName "demo1_interrupt_approval_basic.py"),
    (Join-Path $section2.FullName "demo2_refund_approval_workflow.py"),
    (Join-Path $section2.FullName "demo3_edit_before_send.py")
)

foreach ($demo in $demos) {
    Write-Host ""
    Write-Host "=== Running $demo ==="
    python $demo
    if ($LASTEXITCODE -ne 0) {
        throw "Demo failed: $demo"
    }
}

Write-Host ""
Write-Host "All Week 6 demos ran successfully."
