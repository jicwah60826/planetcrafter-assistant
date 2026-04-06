<#
.SYNOPSIS
    Parses Planet Crafter Unity MonoBehaviour .asset files and produces
    a recipes.json-compatible JSON array, ready to merge into
    wwwroot/data/recipes.json.

.DESCRIPTION
    Pass 1 – Build a GUID → item name lookup from every .asset file.
    Pass 2 – Find all assets that have recipeIngredients.
    Pass 3 – For each such asset, resolve ingredient GUIDs to names,
             find the icon PNG (via the .meta sidecar of the icon GUID's asset),
             and emit a JSON entry matching the existing recipes.json schema.

.PARAMETER AssetsRoot
    Path to the exported MonoBehaviour folder.
    Default: D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\MonoBehaviour

.PARAMETER OutputFile
    Path where the resulting JSON file is written.
    Default: D:\PlanetCrafterAssistant\Tools\extracted_recipes.json

.PARAMETER IconSearchRoot
    Root under which PNG sprite files live (searched recursively).
    Default: D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets

.PARAMETER IconOutputDir
    Destination folder for copied PNG icons when -ExportIcons is set.
    Default: D:\PlanetCrafterAssistant\App\wwwroot\images\icons

.PARAMETER ExportIcons
    When set, copies each resolved icon PNG to IconOutputDir.

.EXAMPLE
    .\Parse-AssetRecipes.ps1
    .\Parse-AssetRecipes.ps1 -ExportIcons
    .\Parse-AssetRecipes.ps1 -AssetsRoot "C:\MyDump\MonoBehaviour" -OutputFile "C:\out.json"
#>

param(
    [string]$AssetsRoot     = "D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\MonoBehaviour",
    [string]$OutputFile     = "D:\PlanetCrafterAssistant\Tools\extracted_recipes.json",
    [string]$IconSearchRoot = "D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets",
    [string]$IconOutputDir  = "D:\PlanetCrafterAssistant\App\wwwroot\images\icons",
    [switch]$ExportIcons
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-AssetField([string[]]$lines, [string]$field) {
    foreach ($line in $lines) {
        if ($line -match "^\s+${field}:\s*(.+)$") {
            # Strip null bytes / non-printable chars caused by UTF-16 files
            # being read without explicit encoding
            return ($Matches[1].Trim() -replace '[^\x20-\x7E\u00A0-\uFFFF]', '')
        }
    }
    return $null
}

function Get-GuidFromRef([string]$refValue) {
    if ($refValue -match 'guid:\s*([0-9a-f]+)') {
        return $Matches[1]
    }
    return $null
}

function Build-GuidToFilePath([string]$root) {
    $map = @{}
    Get-ChildItem -Path $root -Filter "*.asset.meta" -Recurse | ForEach-Object {
        $metaContent = Get-Content $_.FullName -Raw -Encoding UTF8
        if ($metaContent -match 'guid:\s*([0-9a-f]+)') {
            $guid      = $Matches[1]
            $assetPath = $_.FullName -replace '\.meta$', ''
            if (Test-Path $assetPath) {
                $map[$guid] = $assetPath
            }
        }
    }
    return $map
}

function Build-GuidToId([hashtable]$guidToPath) {
    $map = @{}
    foreach ($entry in $guidToPath.GetEnumerator()) {
        $guid = $entry.Key
        $path = $entry.Value
        try {
            # UTF8 encoding prevents null-byte spacing on UTF-16 asset files
            $lines = Get-Content $path -Encoding UTF8
            $id    = Get-AssetField $lines "id"
            if ($id) { $map[$guid] = $id }
        } catch { <# skip unreadable files #> }
    }
    return $map
}

function Resolve-IconPath([string]$iconGuid, [string]$searchRoot) {
    if (-not $iconGuid) { return $null }
    $hit = Get-ChildItem -Path $searchRoot -Recurse -Include "*.png.meta", "*.png" |
        Where-Object { $_.Name -match '\.meta$' } |
        ForEach-Object {
            $content = Get-Content $_.FullName -Raw -Encoding UTF8
            if ($content -match 'guid:\s*([0-9a-f]+)') {
                if ($Matches[1] -eq $iconGuid) {
                    $_.FullName -replace '\.meta$', ''
                }
            }
        } | Select-Object -First 1
    return $hit
}

function Map-Category([string]$raw) {
    switch ($raw) {
        "0"  { return "Raw" }
        "1"  { return "Resource" }
        "2"  { return "Equipment" }
        "3"  { return "Structure" }
        "4"  { return "Machine" }
        "5"  { return "Energy" }
        "6"  { return "Machine" }
        "7"  { return "Rocket" }
        "8"  { return "Automation" }
        "9"  { return "Toxicity" }
        "10" { return "Storage" }
        default { return "Resource" }
    }
}

function Map-WorldUnit([string]$raw) {
    switch ($raw) {
        "1"  { return "Heat" }
        "2"  { return "Pressure" }
        "3"  { return "Oxygen" }
        "4"  { return "Biomass" }
        "5"  { return "Insects" }
        "6"  { return "Animals" }
        "7"  { return "Humidity" }
        default { return $null }
    }
}

function Map-WorldUnit-Unit([string]$stage) {
    switch ($stage) {
        "Heat"     { return "nK" }
        "Pressure" { return "µPa" }
        "Oxygen"   { return "ppm" }
        default    { return "units" }
    }
}

# ---------------------------------------------------------------------------
# Pass 1 – GUID ↔ file path  &  GUID ↔ id
# ---------------------------------------------------------------------------

Write-Host "Pass 1: Building GUID maps from $AssetsRoot ..."
$guidToPath = Build-GuidToFilePath $AssetsRoot
$guidToId   = Build-GuidToId $guidToPath
Write-Host "  $($guidToPath.Count) asset files indexed."

# ---------------------------------------------------------------------------
# Pass 2 – Find all assets with recipeIngredients
# ---------------------------------------------------------------------------

Write-Host "Pass 2: Scanning for assets with recipeIngredients ..."
$craftableAssets = Get-ChildItem -Path $AssetsRoot -Filter "*.asset" -Recurse |
    Where-Object { (Get-Content $_.FullName -Raw -Encoding UTF8) -match 'recipeIngredients:' }
Write-Host "  $($craftableAssets.Count) craftable assets found."

# ---------------------------------------------------------------------------
# Pass 3 – Extract data and build recipe objects
# ---------------------------------------------------------------------------

Write-Host "Pass 3: Extracting recipe data ..."
$results = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($assetFile in $craftableAssets) {
    $lines = Get-Content $assetFile.FullName -Encoding UTF8

    # --- Item identity ---
    $itemId = Get-AssetField $lines "id"
    if (-not $itemId) { $itemId = $assetFile.BaseName }

    # --- Friendly display name: "AnimalFeeder1" → "Animal Feeder T1" ---
    $displayName = $itemId `
        -replace '(?<=[a-z0-9])([A-Z])', ' $1' `
        -replace '\s+(\d+)$', ' T$1'

    # --- Category ---
    $groupCat = Get-AssetField $lines "groupCategory"
    if (-not $groupCat) { $groupCat = "" }
    $category = Map-Category $groupCat

    # --- Icon GUID → PNG filename ---
    $iconLine     = ($lines | Where-Object { $_ -match '^\s+icon:' } | Select-Object -First 1)
    $iconGuid     = if ($iconLine) { Get-GuidFromRef $iconLine } else { $null }
    $iconFullPath = Resolve-IconPath $iconGuid $IconSearchRoot
    $iconFile     = $null
    if ($iconFullPath) {
        $iconFile = Split-Path $iconFullPath -Leaf
        if ($ExportIcons) {
            if (-not (Test-Path $IconOutputDir)) {
                New-Item -ItemType Directory -Path $IconOutputDir | Out-Null
            }
            $destPath = Join-Path $IconOutputDir $iconFile
            if (-not (Test-Path $destPath)) {
                Copy-Item -Path $iconFullPath -Destination $destPath
            }
        }
    }

    # --- Ingredients ---
    $ingredientGuids = [System.Collections.Generic.List[string]]::new()
    $inBlock = $false
    foreach ($line in $lines) {
        if ($line -match '^\s+recipeIngredients:') {
            $inBlock = $true
            continue
        }
        if ($inBlock) {
            if ($line -match '^\s+-\s+\{') {
                $g = Get-GuidFromRef $line
                if ($g) { $ingredientGuids.Add($g) }
            } elseif ($line -match '^\s+\w+:' -and $line -notmatch '^\s+-') {
                $inBlock = $false
            }
        }
    }

    $ingredients = $ingredientGuids | ForEach-Object {
        $resolvedId = $guidToId[$_]
        if ($resolvedId) {
            $friendlyName = $resolvedId `
                -replace '\d+$', '' `
                -replace '(?<=[a-z0-9])([A-Z])', ' $1'
            [PSCustomObject]@{ name = $friendlyName; quantity = 1 }
        }
    } | Where-Object { $_ -ne $null } |
        Group-Object -Property name |
        ForEach-Object {
            [PSCustomObject]@{
                name     = $_.Name
                quantity = ($_.Group | Measure-Object -Property quantity -Sum).Sum
            }
        }

    if ($null -eq $ingredients) {
        $ingredients = @()
    } else {
        $ingredients = @($ingredients)
    }
    $ingredientCount = $ingredients.Count

    # --- Unlock condition ---
    $worldUnit  = Get-AssetField $lines "unlockingWorldUnit"
    $worldValue = Get-AssetField $lines "unlockingValue"
    if (-not $worldUnit)  { $worldUnit  = "" }
    if (-not $worldValue) { $worldValue = "0" }

    $stage           = Map-WorldUnit $worldUnit
    $unlockCondition = $null
    if ($stage -and [double]$worldValue -gt 0) {
        $unlockCondition = [PSCustomObject]@{
            stage     = $stage
            threshold = [double]$worldValue
            unit      = (Map-WorldUnit-Unit $stage)
        }
    }

    $recipe = [PSCustomObject]@{
        name            = $displayName
        category        = $category
        description     = ""
        ingredients     = $ingredients
        unlockCondition = $unlockCondition
        craftedIn       = if ($ingredientCount -gt 0) { "Crafting Table" } else { $null }
        recyclerYields  = ($ingredientCount -gt 0)
        _sourceAsset    = $assetFile.Name
        _iconFile       = $iconFile
    }
    $results.Add($recipe)
}

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

$outputDir = Split-Path $OutputFile -Parent
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

$json = $results | ConvertTo-Json -Depth 10
Set-Content -Path $OutputFile -Value $json -Encoding UTF8

Write-Host ""
Write-Host "Done. $($results.Count) recipes written to:"
Write-Host "  $OutputFile"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review extracted_recipes.json — check _sourceAsset and _iconFile columns"
Write-Host "  2. Fill in 'description' fields (or pull from localization .asset files)"
Write-Host "  3. Verify ingredient names match exactly what is in your recipes.json"
Write-Host "  4. Remove _sourceAsset and _iconFile helper fields before merging"
Write-Host "  5. Merge into wwwroot/data/recipes.json"