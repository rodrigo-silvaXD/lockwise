<#
.SYNOPSIS
    Sobe o gateway apontando para a API na nuvem.

.DESCRIPTION
    Evita ter que digitar variaveis de ambiente na hora da apresentacao.
    O gateway roda NESTA maquina, ao lado do Logisim; a API fica no Render.

.PARAMETER Chave
    A LOCKWISE_API_KEY, copiada do painel do Render (Environment).
    Se omitida, usa a que ja estiver no ambiente.

.PARAMETER Url
    A URL da API. Padrao: o servico em producao.

.PARAMETER Roteiro
    Executa um arquivo de comandos em vez de abrir o modo interativo.
    Use roteiros/demo.txt para o ensaio completo.

.EXAMPLE
    .\demo.ps1 -Chave "cole-a-chave-aqui"
    Abre o painel interativo contra a nuvem.

.EXAMPLE
    .\demo.ps1 -Chave "cole-a-chave-aqui" -Roteiro roteiros/demo.txt
    Roda o ensaio inteiro: acesso liberado, tres erros, bloqueio, desbloqueio.

.EXAMPLE
    .\demo.ps1 -Url http://127.0.0.1:8000 -Chave dev
    Contra a API rodando na propria maquina.
#>
param(
    [string]$Chave = $env:LOCKWISE_API_KEY,
    [string]$Url = "https://lockwise-api.onrender.com",
    [string]$Roteiro = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($Chave)) {
    Write-Host "Falta a chave da API." -ForegroundColor Red
    Write-Host "Pegue em: painel do Render > servico lockwise-api > Environment > LOCKWISE_API_KEY"
    Write-Host "Depois rode:  .\demo.ps1 -Chave `"a-chave`""
    exit 1
}

$env:LOCKWISE_API_URL = $Url
$env:LOCKWISE_API_KEY = $Chave

Write-Host "API:     $Url" -ForegroundColor Cyan
Write-Host "Circuito: abra circuito/lockwise_completo.circ no Logisim e acompanhe os mesmos pinos" -ForegroundColor Cyan
Write-Host ""

if ([string]::IsNullOrWhiteSpace($Roteiro)) {
    python -m lockwise_gateway.cli
} else {
    python -m lockwise_gateway.cli --roteiro $Roteiro
}
