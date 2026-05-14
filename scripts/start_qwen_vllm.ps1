param(
    [string]$ModelPath = ".\Qwen2.5-7B-Instruct",
    [string]$ServedModelName = "qwen2.5-7b-instruct",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8001,
    [int]$GpuMemoryUtilization = 85
)

$ErrorActionPreference = "Stop"

$resolvedModelPath = (Resolve-Path -LiteralPath $ModelPath).Path
$indexPath = Join-Path $resolvedModelPath "model.safetensors.index.json"

if (-not (Test-Path -LiteralPath $indexPath)) {
    throw "Missing $indexPath. Please make sure the Qwen model directory is complete."
}

$index = Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json
$missingFiles = $index.weight_map.PSObject.Properties.Value |
    Sort-Object -Unique |
    Where-Object { -not (Test-Path -LiteralPath (Join-Path $resolvedModelPath $_)) }

if ($missingFiles) {
    throw "Missing Qwen model shard(s): $($missingFiles -join ', '). Please finish downloading the model first."
}

python -c "import vllm" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "vLLM is not installed in the current Python environment. Install vLLM, or use another OpenAI-compatible local model server and keep .env pointed at http://localhost:8001/v1."
}

python -m vllm.entrypoints.openai.api_server `
    --model $resolvedModelPath `
    --served-model-name $ServedModelName `
    --host $HostName `
    --port $Port `
    --gpu-memory-utilization ($GpuMemoryUtilization / 100) `
    --enable-auto-tool-choice `
    --tool-call-parser hermes
