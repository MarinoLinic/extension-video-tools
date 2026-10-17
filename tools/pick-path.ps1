param([ValidateSet('folder','cookies')][string]$Kind)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
if($Kind -eq 'folder') {
    $dialog=New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description='Choose where Video Tools saves downloads'
} else {
    $dialog=New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title='Choose a Netscape cookies file (optional)'
    $dialog.Filter='Cookie files (*.txt)|*.txt|All files (*.*)|*.*'
}
try {
    if($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $selected=if($Kind -eq 'folder'){$dialog.SelectedPath}else{$dialog.FileName}
        [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($selected))
    }
} finally { $dialog.Dispose() }
