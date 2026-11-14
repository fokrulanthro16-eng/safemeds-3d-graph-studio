& {
  # relate's release signing key: distribution/release-signing-key.pub in github.com/relatedb/relate
  # fingerprint SHA256:BfnIA0YD0h+ldihdq8V1k/xFY91lm8mRCuVS21+3kzA
  $signingKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHgv/GHY5mtv/HopH/J/T7KrTT7eOVFEG2ueT4iRKwbK relate-release'
  $ErrorActionPreference = 'Stop'
  $ProgressPreference = 'SilentlyContinue'
  if (-not (Get-Command ssh-keygen -ErrorAction SilentlyContinue)) { throw 'ssh-keygen not found: add the OpenSSH Client in Settings > System > Optional features, then run this again' }
  $tag = (Invoke-RestMethod https://relatedb.ai/releases.json).latest.tag
  $url = "https://github.com/relatedb/relate/releases/download/$tag"
  $tmp = Join-Path ([IO.Path]::GetTempPath()) "relate-install-$tag"
  New-Item -ItemType Directory -Force $tmp | Out-Null
  Invoke-WebRequest "$url/SHA256SUMS" -OutFile "$tmp\SHA256SUMS" -UseBasicParsing
  Invoke-WebRequest "$url/SHA256SUMS.sig" -OutFile "$tmp\SHA256SUMS.sig" -UseBasicParsing
  [IO.File]::WriteAllText("$tmp\allowed_signers", "relate-release $signingKey`n")
  $verify = Start-Process ssh-keygen -ArgumentList '-Y verify -f allowed_signers -I relate-release -n relate-release -s SHA256SUMS.sig' -WorkingDirectory $tmp -RedirectStandardInput "$tmp\SHA256SUMS" -NoNewWindow -Wait -PassThru
  if ($verify.ExitCode -ne 0) { throw "the SHA256SUMS signature check failed for $tag; installing nothing" }
  $sums = @(Get-Content "$tmp\SHA256SUMS")
  if ($sums[0].Trim() -ne "# relate-release-version: $tag") { throw "SHA256SUMS does not name $tag on its signed first line; installing nothing" }
  $line = $sums | Where-Object { $_ -match '^[0-9a-f]{64}\s+relate-windows-amd64\.exe$' } | Select-Object -First 1
  if (-not $line) { throw "SHA256SUMS has no entry for relate-windows-amd64.exe; installing nothing" }
  Invoke-WebRequest "$url/relate-windows-amd64.exe" -OutFile "$tmp\relate.exe" -UseBasicParsing
  if ((Get-FileHash "$tmp\relate.exe" -Algorithm SHA256).Hash -ne ($line -split '\s+')[0]) { throw "relate-windows-amd64.exe does not match its SHA-256 in SHA256SUMS; installing nothing" }
  $dir = Join-Path $env:LOCALAPPDATA 'Programs\relate'
  New-Item -ItemType Directory -Force $dir | Out-Null
  Move-Item -Force "$tmp\relate.exe" "$dir\relate.exe"
  Remove-Item -Recurse -Force $tmp
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if (("$userPath" -split ';') -notcontains $dir) { [Environment]::SetEnvironmentVariable('Path', ((@("$userPath" -split ';') -ne '') + $dir) -join ';', 'User') }
  if (($env:Path -split ';') -notcontains $dir) { $env:Path = "$env:Path;$dir" }
  "Installed relate $tag at $dir\relate.exe"
}
