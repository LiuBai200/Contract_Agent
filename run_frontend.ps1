param(
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not available. Please install Node.js and npm first."
}

Set-Location ".\frontend"
npm install
npm run dev -- --host 127.0.0.1 --port $Port
