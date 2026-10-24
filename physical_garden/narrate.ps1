param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$out = Join-Path $PSScriptRoot "output"
$segments = Get-Content -LiteralPath (Join-Path $out "narration.json") -Raw | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
try {
    for ($i=0; $i -lt $segments.Count; $i++) {
        $synth.SetOutputToWaveFile((Join-Path $out "narration_$i.wav"))
        $synth.Speak($segments[$i].text)
        $synth.SetOutputToNull()
    }
} finally { $synth.Dispose() }
& $Python -m physical_garden.audio
if ($LASTEXITCODE -ne 0) { throw "Audio assembly failed" }
