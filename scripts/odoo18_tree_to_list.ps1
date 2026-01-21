# C:\odoo_dev\scripts\odoo18_tree_to_list.ps1
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [string]$Root = (Join-Path (Get-Location) "addons\common\itad_core\views"),

    [Parameter(Mandatory = $false)]
    [switch]$Backup,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Update-ViewMode([string]$text) {
    # Replace tree token inside <field name="view_mode">...</field>
    return [regex]::Replace(
        $text,
        '(?s)(<field\s+name="view_mode"\s*>\s*)([^<]*?)(\s*</field>)',
        {
            param($m)
            $prefix = $m.Groups[1].Value
            $mode = $m.Groups[2].Value
            $suffix = $m.Groups[3].Value

            # replace tokens only, keep order
            $mode2 = ($mode -split '\s*,\s*') | ForEach-Object {
                if ($_ -eq 'tree') { 'list' } else { $_ }
            }
            $modeJoined = ($mode2 -join ',')
            return "$prefix$modeJoined$suffix"
        }
    )
}

function Update-TreeTags([string]$text) {
    $t = $text
    # XML arch root tags
    $t = $t -replace '<tree(\b|>)', '<list$1'
    $t = $t -replace '</tree>', '</list>'

    # Some XPath exprs refer to tree
    $t = $t -replace '//tree\b', '//list'
    $t = $t -replace '\/tree\b', '/list'
    return $t
}

function Normalize([string]$text) {
    $t = $text
    $t = Update-ViewMode $t
    $t = Update-TreeTags $t
    return $t
}

if (-not (Test-Path $Root)) {
    throw "Root folder not found: $Root"
}

$files = Get-ChildItem $Root -Recurse -Filter *.xml | Sort-Object FullName
if ($files.Count -eq 0) {
    Write-Host "No XML files found under $Root"
    exit 0
}

$changed = 0
foreach ($f in $files) {
    $path = $f.FullName
    $orig = Get-Content $path -Raw
    $new = Normalize $orig

    if ($new -ne $orig) {
        $changed++
        Write-Host "CHANGE: $path"

        if ($DryRun) { continue }

        if ($Backup) {
            $bak = "$path.bak"
            if (-not (Test-Path $bak)) {
                Copy-Item $path $bak -Force
            }
        }

        if ($PSCmdlet.ShouldProcess($path, "Apply tree->list + view_mode fixes")) {
            Set-Content -Path $path -Value $new -NoNewline
        }
    }
}

Write-Host "Done. Files changed: $changed"
Write-Host "Tip: run a quick scan:"
Write-Host "  Select-String -Recurse -Path $Root -Pattern '<tree|</tree>|view_mode.*tree|>tree<'"
