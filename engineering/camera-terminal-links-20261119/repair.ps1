$ErrorActionPreference = 'Stop'
$base = Join-Path (Get-Location) 'engineering/camera-terminal-links-20261119'
$projectFile = Join-Path (Get-Location) 'TwinCAT Patch Press/TwinCAT Patch Press.tsproj'
$dte = [Runtime.InteropServices.Marshal]::GetActiveObject('VisualStudio.DTE.17.0')
if ($dte.Solution.FullName -ne (Join-Path (Get-Location) 'TE1108_PatchPress.sln')) { throw 'Wrong solution' }
$project = $dte.Solution.Projects.Item(1)
$system = $project.Object
$inputRoot = 'TIPC^PatchPress^PatchPress Instance^PlcTask Inputs^GVL_EtherCAT.'
$ioRoot = 'TIID^Device 1 (EtherCAT)^Term 1 (EK1100)^'
$links = @()
foreach ($channel in 1..4) {
    $links += [pscustomobject]@{
        Source = $inputRoot + 'stTerm21_EL3314.iEL3314_Ch' + $channel
        Target = $ioRoot + 'Term 21 (EL3314-0092)^TC Inputs Channel ' + $channel + '^Value'
        Type = 'DINT'; Bits = 32
    }
}
foreach ($terminal in @('20_EL4022', '21_EL3314', '22_EL6633')) {
    $number, $model = $terminal.Split('_')
    if ($model -eq 'EL3314') { $model = 'EL3314-0092' }
    $links += [pscustomobject]@{
        Source = $inputRoot + 'stTerm' + $terminal + '.stTerminalInfo.nTerminal_State'
        Target = $ioRoot + 'Term ' + $number + ' (' + $model + ')^InfoData^State'
        Type = 'UINT'; Bits = 16
    }
}
[xml]$beforeMapping = $system.ProduceMappingInfo()
# Validate every endpoint and reject existing links before making any change.
foreach ($link in $links) {
    foreach ($path in @($link.Source, $link.Target)) {
        [xml]$endpoint = $system.LookupTreeItem($path).ProduceXml($false)
        if ($endpoint.TreeItem.VarDef.VarType.InnerText -ne $link.Type -or
            [int]$endpoint.TreeItem.VarDef.VarBitSize -ne $link.Bits) {
            throw ('Unexpected endpoint type: ' + $path + ' ' + $endpoint.OuterXml)
        }
    }
    $relativeSource = $link.Source.Substring('TIPC^PatchPress^PatchPress Instance^'.Length)
    foreach ($existing in $beforeMapping.SelectNodes('//Link')) {
        if ($existing.VarA -eq $relativeSource -or
            ($existing.ParentNode.Name + '^' + $existing.VarB) -eq $link.Target) {
            throw ('Endpoint already linked: ' + $link.Source)
        }
    }
}
if (Test-Path (Join-Path $base 'before.tsproj')) { throw 'Backup exists; inspect before rerunning' }
Copy-Item -LiteralPath $projectFile -Destination (Join-Path $base 'before.tsproj')
[IO.File]::WriteAllText((Join-Path $base 'mapping-before.xml'), $beforeMapping.OuterXml)
$links | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $base 'links.json') -Encoding UTF8
git status --short | Set-Content -LiteralPath (Join-Path $base 'status-before.txt')
git diff --binary | Set-Content -LiteralPath (Join-Path $base 'diff-before.txt')
foreach ($link in $links) { $system.LinkVariables($link.Source, $link.Target) }
[xml]$afterMapping = $system.ProduceMappingInfo()
[IO.File]::WriteAllText((Join-Path $base 'mapping-after.xml'), $afterMapping.OuterXml)
foreach ($link in $links) {
    $relativeSource = $link.Source.Substring('TIPC^PatchPress^PatchPress Instance^'.Length)
    $matches = @($afterMapping.SelectNodes('//Link') | Where-Object {
        $_.VarA -eq $relativeSource -and ($_.ParentNode.Name + '^' + $_.VarB) -eq $link.Target
    })
    if ($matches.Count -ne 1) { throw ('Readback mismatch: ' + $link.Source) }
}
$project.Save()
[xml]$saved = Get-Content -LiteralPath $projectFile
foreach ($link in $links) {
    $relativeSource = $link.Source.Substring('TIPC^PatchPress^PatchPress Instance^'.Length)
    $matches = @($saved.SelectNodes('//Mappings//Link') | Where-Object {
        $_.VarA -eq $relativeSource -and ($_.ParentNode.Name + '^' + $_.VarB) -eq $link.Target
    })
    if ($matches.Count -ne 1) { throw ('Saved mapping mismatch: ' + $link.Source) }
}
'Verified and saved seven offline links. No activation, download or ADS access.'
