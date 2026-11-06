$ErrorActionPreference = 'Stop'
$mappingDte = [Runtime.InteropServices.Marshal]::GetActiveObject('VisualStudio.DTE.17.0')
if ($mappingDte.Solution.FullName -ne (Join-Path (Get-Location) 'TE1108_PatchPress.sln')) { throw 'Wrong solution' }
$mappingStarted = [DateTime]::UtcNow
$mappingDte.Solution.SolutionBuild.BuildProject('Release|TwinCAT HMI', 'TwinCAT Patch Press\PatchPress_HMI\PatchPress_HMI.hmiproj', $true)
$mappingResult = [ordered]@{
    StartedUtc = $mappingStarted.ToString('o')
    FinishedUtc = [DateTime]::UtcNow.ToString('o')
    FailedProjects = $mappingDte.Solution.SolutionBuild.LastBuildInfo
    BuildState = [string]$mappingDte.Solution.SolutionBuild.BuildState
}
$mappingResult | ConvertTo-Json | Set-Content engineering/hmi-io/corrected-hmi-build-result.json
$mappingResult | ConvertTo-Json
if ($mappingResult.FailedProjects -ne 0) { exit 1 }
