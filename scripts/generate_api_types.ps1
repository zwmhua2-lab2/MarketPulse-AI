$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Push-Location frontend
npm run generate:api
Pop-Location

