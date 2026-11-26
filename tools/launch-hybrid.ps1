# Launch the hybrid build with the 8 GB switch set.
#
#   $env:VICTORY_GAME_DIR = 'D:\Games\MyDump'      # your own dump, required
#   .\tools\launch-hybrid.ps1                      # release build, no HUD
#   .\tools\launch-hybrid.ps1 -Diag -Hud -Seconds 600
#
# Placeholder: an empty string for a switch falls back to the build's default.

param(
    [switch]$Diag,                      # target/diag (release + diagnostics) instead of target/release
    [switch]$Hud,                       # attach tools/hud.py overlay
    [int]$Seconds = 0,                  # 0 runs until the title exits
    [int]$DropMips = 1,                 # 0..4: largest mip levels the host copy leaves out
    [string]$Log = ''
)

$ErrorActionPreference = 'Stop'
if (-not $env:VICTORY_GAME_DIR) { throw 'set VICTORY_GAME_DIR to your own dump of the title' }

$root = Split-Path -Parent $PSScriptRoot
$buildProfile = if ($Diag) { 'diag' } else { 'release' }
$exe = Join-Path $root "target/$buildProfile/victory.exe"
if (-not (Test-Path $exe)) {
    throw "missing $exe; build it first: cargo build --locked --profile $buildProfile -p victory"
}

$cache = Join-Path $env:LOCALAPPDATA 'victory/cache-hybrid-8gb'
$data = Join-Path $env:LOCALAPPDATA 'victory/data-hybrid-8gb'
if (-not $Log) { $Log = Join-Path $cache 'run.log' }
$hudSwitch = if ($Hud) { '1' } else { '0' }

$settings = @{
    # The pareto-residency set the codec_d launcher picks, plus the 8 GB patch.
    VICTORY_AMBIENT_AIR = '1.5'; VICTORY_TEXTURE_NO_WAIT = '1'; VICTORY_RELAY = '2'
    VICTORY_WIDE_BACK = '1'; VICTORY_CARD_REHASH_RUNS = '1'; VICTORY_JOIN_COPIES = '1'
    VICTORY_INDIRECT_WINDOW = '1'; VICTORY_RELAY_COPY = '1'; VICTORY_CARD_STEPS = '2'
    VICTORY_INDIRECT_BATCH = '2'; VICTORY_MAP_THREADS = '1'; VICTORY_CARD_AWAKE = '1'
    VICTORY_SHOW_AFTER = '1'; VICTORY_AMBIENT = '0.8'; VICTORY_THIN = '1'
    VICTORY_JOIN_PARTS = '8'; VICTORY_UPLOAD_AHEAD = '1'; VICTORY_LEVELS_ON_DEMAND = '1'
    VICTORY_CARD_BUFFERS_MIN_KB = '64'; VICTORY_LOG = 'info'
    VICTORY_TEXTURE_DROP_MIPS = "$DropMips"
    CONSOLE = 'series-s'; HUD = $hudSwitch; CLICK_LIMIT = '0'
}
foreach ($entry in $settings.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
}

Push-Location $root
try {
    & python tools/run_ab.py "$Seconds" $Log $exe $cache $data
} finally {
    Pop-Location
}
