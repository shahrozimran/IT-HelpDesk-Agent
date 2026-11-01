$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PIP_CACHE_DIR = Join-Path $PSScriptRoot '.cache\pip'
$env:TMP = Join-Path $PSScriptRoot 'tmp\install'
$env:TEMP = $env:TMP
New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR,$env:TMP | Out-Null
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12, then rerun setup.ps1.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$pineconeReady = & '.\.venv\Scripts\python.exe' -c "from src.config import Settings; s=Settings(); print(int(bool(s.pinecone_api_key and s.pinecone_host)))"
if ($pineconeReady -eq '1') {
    & '.\.venv\Scripts\python.exe' scripts/ingest_documents.py
    if ($LASTEXITCODE -ne 0) { throw 'Pinecone ingestion failed. Check connection settings and index dimensions.' }
} else {
    & '.\.venv\Scripts\python.exe' scripts/ingest_documents.py --prepare-only
    Write-Output 'Pinecone connection details are pending. Complete .env, then run scripts/ingest_documents.py.'
}
Write-Output 'Setup complete. Configure .env, then run .\run.ps1.'
