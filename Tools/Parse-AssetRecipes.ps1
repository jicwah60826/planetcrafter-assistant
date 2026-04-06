<#
.SYNOPSIS
    Parses Planet Crafter Unity MonoBehaviour .asset files and produces
    a recipes.json-compatible JSON array ready to merge into
    wwwroot/data/recipes.json.

.PARAMETER AssetsRoot
    Path to the MonoBehaviour folder containing craftable item assets.
    Default: D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\MonoBehaviour

.PARAMETER ExportRoot
    Root of the entire AssetRipper export - searched recursively for .meta files
    and ingredient .asset files.
    Default: D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject

.PARAMETER OutputFile
    Path where the resulting JSON file is written.
    Default: D:\PlanetCrafterAssistant\Tools\extracted_recipes.json

.PARAMETER IconOutputDir
    Destination folder for copied PNG icons when -ExportIcons is set.
    Default: D:\PlanetCrafterAssistant\App\wwwroot\images\icons

.PARAMETER ExportIcons
    When set, copies each resolved icon PNG to IconOutputDir.

.EXAMPLE
    .\Parse-AssetRecipes.ps1
    .\Parse-AssetRecipes.ps1 -ExportIcons
#>

param(
    [string]$AssetsRoot   = "D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\MonoBehaviour",
    [string]$ExportRoot   = "D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject",
    [string]$OutputFile   = "D:\PlanetCrafterAssistant\Tools\extracted_recipes.json",
    [string]$IconOutputDir = "D:\PlanetCrafterAssistant\App\wwwroot\images\icons",
    [switch]$ExportIcons
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-AssetField([string[]]$lines, [string]$field) {
    foreach ($line in $lines) {
        if ($line -match "^\s*${field}:\s*(.+)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

function Get-GuidFromRef([string]$refValue) {
    if ($refValue -match 'guid:\s*([0-9a-fA-F]{32})') {
        return $Matches[1].ToLower()
    }
    return $null
}

function Read-Lines([string]$path) {
    # Try Unicode (UTF-16 LE) first — standard for Unity/AssetRipper exports
    try {
        return Get-Content $path -Encoding Unicode
    } catch {
        return Get-Content $path -Encoding UTF8
    }
}

# ---------------------------------------------------------------------------
# Pass 1 – Build GUID → id map using .meta sidecar files
#           .meta files are searched across the ENTIRE export root, not just
#           MonoBehaviour — ingredient assets may live in subfolders.
# ---------------------------------------------------------------------------

Write-Host "Pass 1: Scanning for .meta files under $ExportRoot ..."
$guidToId   = @{}
$guidToPath = @{}

$metaFiles = @(Get-ChildItem -Path $ExportRoot -Filter "*.meta" -Recurse)
Write-Host "  $($metaFiles.Count) .meta files found."

foreach ($meta in $metaFiles) {
    try {
        $metaContent = Read-Lines $meta.FullName
        $guid = $null
        foreach ($line in $metaContent) {
            if ($line -match '^\s*guid:\s*([0-9a-fA-F]{32})') {
                $guid = $Matches[1].ToLower()
                break
            }
        }
        if (-not $guid) { continue }

        # The asset this .meta belongs to is the same path minus ".meta"
        $assetPath = $meta.FullName -replace '\.meta$', ''
        if (-not (Test-Path $assetPath)) { continue }

        $guidToPath[$guid] = $assetPath

        # Try to read the id: field from the asset
        $assetLines = Read-Lines $assetPath
        $id = Get-AssetField $assetLines "id"
        if ($id) {
            $guidToId[$guid] = $id
        }
    } catch { <# skip unreadable files #> }
}

Write-Host "  $($guidToId.Count) GUID → id entries indexed."

# ---------------------------------------------------------------------------
# Pass 2 – Find craftable assets (those with recipeIngredients)
# ---------------------------------------------------------------------------

Write-Host "Pass 2: Scanning $AssetsRoot for assets with recipeIngredients ..."
$allMono = @(Get-ChildItem -Path $AssetsRoot -Filter "*.asset" -Recurse)
Write-Host "  $($allMono.Count) MonoBehaviour assets found."

$craftableAssets = @($allMono | Where-Object {
    $content = (Read-Lines $_.FullName) -join "`n"
    $content -match 'recipeIngredients:'
})
Write-Host "  $($craftableAssets.Count) craftable assets found."

# ---------------------------------------------------------------------------
# Pass 3 – Extract and emit recipe objects
# ---------------------------------------------------------------------------

Write-Host "Pass 3: Extracting recipe data ..."

$categoryMap = @{
    "0"="Raw"; "1"="Resource"; "2"="Equipment"; "3"="Structure";
    "4"="Machine"; "5"="Energy"; "6"="Machine"; "7"="Rocket";
    "8"="Automation"; "9"="Toxicity"; "10"="Storage"
}
$worldUnitMap = @{
    "1"="Heat"; "2"="Pressure"; "3"="Oxygen";
    "4"="Biomass"; "5"="Insects"; "6"="Animals"; "7"="Humidity"
}
$unitLabelMap = @{ "Heat"="nK"; "Pressure"="µPa"; "Oxygen"="ppm" }

$results = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($assetFile in $craftableAssets) {
    $lines = Read-Lines $assetFile.FullName

    # --- Item identity ---
    $itemId = Get-AssetField $lines "id"
    if (-not $itemId) { $itemId = $assetFile.BaseName }

    # PascalCase → "Pascal Case", trailing digit → " T#"
    $displayName = $itemId `
        -replace '(?<=[a-z0-9])([A-Z])', ' $1' `
        -replace '\s+(\d+)$', ' T$1'

    # --- Category ---
    $groupCat = Get-AssetField $lines "groupCategory"
    if (-not $groupCat) { $groupCat = "" }
    $category = if ($categoryMap.ContainsKey($groupCat)) { $categoryMap[$groupCat] } else { "Resource" }

    # --- Icon ---
    $iconLine = ($lines | Where-Object { $_ -match '^\s+icon:' } | Select-Object -First 1)
    $iconGuid = if ($iconLine) { Get-GuidFromRef $iconLine } else { $null }
    $iconFile = $null
    if ($iconGuid -and $guidToPath.ContainsKey($iconGuid)) {
        $iconSrcPath = $guidToPath[$iconGuid]
        if ($iconSrcPath -match '\.png$') {
            $iconFile = Split-Path $iconSrcPath -Leaf
            if ($ExportIcons) {
                if (-not (Test-Path $IconOutputDir)) {
                    New-Item -ItemType Directory -Path $IconOutputDir | Out-Null
                }
                $dest = Join-Path $IconOutputDir $iconFile
                if (-not (Test-Path $dest)) {
                    Copy-Item -Path $iconSrcPath -Destination $dest
                }
            }
        }
    }

    # --- Ingredients ---
    $ingredientGuids = [System.Collections.Generic.List[string]]::new()
    $inBlock = $false
    foreach ($line in $lines) {
        if ($line -match '^\s+recipeIngredients:') { $inBlock = $true; continue }
        if ($inBlock) {
            if ($line -match '^\s+-\s+\{') {
                $g = Get-GuidFromRef $line
                if ($g) { $ingredientGuids.Add($g) }
            } elseif ($line -match '^\s+\w+:' -and $line -notmatch '^\s+-') {
                $inBlock = $false
            }
        }
    }

    $ingredients = @($ingredientGuids | ForEach-Object {
        $resolvedId = if ($guidToId.ContainsKey($_)) { $guidToId[$_] } else { $null }
        if ($resolvedId) {
            $friendly = $resolvedId `
                -replace '\d+$', '' `
                -replace '(?<=[a-z0-9])([A-Z])', ' $1'
            [PSCustomObject]@{ name = $friendly; quantity = 1 }
        }
    } | Where-Object { $_ -ne $null } |
        Group-Object -Property name |
        ForEach-Object {
            [PSCustomObject]@{
                name     = $_.Name
                quantity = ($_.Group | Measure-Object -Property quantity -Sum).Sum
            }
        })

    $ingredientCount = $ingredients.Count

    # --- Unlock condition ---
    $worldUnit  = Get-AssetField $lines "unlockingWorldUnit"
    $worldValue = Get-AssetField $lines "unlockingValue"
    if (-not $worldUnit)  { $worldUnit  = "" }
    if (-not $worldValue) { $worldValue = "0" }

    $stage           = if ($worldUnitMap.ContainsKey($worldUnit)) { $worldUnitMap[$worldUnit] } else { $null }
    $unlockCondition = $null
    if ($stage -and [double]$worldValue -gt 0) {
        $unit = if ($unitLabelMap.ContainsKey($stage)) { $unitLabelMap[$stage] } else { "units" }
        $unlockCondition = [PSCustomObject]@{
            stage     = $stage
            threshold = [double]$worldValue
            unit      = $unit
        }
    }

    $results.Add([PSCustomObject]@{
        name            = $displayName
        category        = $category
        description     = ""
        ingredients     = $ingredients
        unlockCondition = $unlockCondition
        craftedIn       = if ($ingredientCount -gt 0) { "Crafting Table" } else { $null }
        recyclerYields  = ($ingredientCount -gt 0)
        _sourceAsset    = $assetFile.Name
        _iconFile       = $iconFile
    })
}

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

$outputDir = Split-Path $OutputFile -Parent
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

$results | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "Done. $($results.Count) recipes written to:"
Write-Host "  $OutputFile"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review extracted_recipes.json — verify names and ingredient counts"
Write-Host "  2. Fill in 'description' fields"
Write-Host "  3. Remove _sourceAsset and _iconFile helper fields before merging"
Write-Host "  4. Merge into wwwroot/data/recipes.json"