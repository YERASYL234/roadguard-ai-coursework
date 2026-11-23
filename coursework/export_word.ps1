param([string]$InputFile,[string]$OutputPdf,[switch]$Update)
$ErrorActionPreference = 'Stop'
$InputFile = [System.IO.Path]::GetFullPath($InputFile)
$OutputPdf = [System.IO.Path]::GetFullPath($OutputPdf)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $null
try {
  $doc = $word.Documents.Open($InputFile, $false, (-not $Update.IsPresent))
  if ($Update) {
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
    $doc.Save()
  }
  $doc.Repaginate()
  Write-Output ('PAGES=' + $doc.ComputeStatistics(2))
  $doc.ExportAsFixedFormat($OutputPdf,17)
  if ($Update) {
    $map = @()
    foreach ($paragraph in $doc.Paragraphs) {
      if ($paragraph.OutlineLevel -le 2) {
        $map += [PSCustomObject]@{text=$paragraph.Range.Text.Trim();page=$paragraph.Range.Information(3)}
      }
    }
    $map | ConvertTo-Json | Set-Content -LiteralPath ($OutputPdf + '.headings.json') -Encoding utf8
  }
} finally {
  if ($null -ne $doc) { $doc.Close(0) }
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
