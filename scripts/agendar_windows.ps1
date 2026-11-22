# Cria uma tarefa no Agendador de Tarefas do Windows para rodar o pipeline todo dia.
#
# Uso (no PowerShell, dentro da pasta do projeto):
#   .\scripts\agendar_windows.ps1                 # todo dia as 07:00
#   .\scripts\agendar_windows.ps1 -Horario 06:30
#   .\scripts\agendar_windows.ps1 -Remover        # apaga a tarefa
#
# O resultado de cada execucao fica em saida\pipeline.log e saida\historico_execucoes.csv.

param(
    [string]$Horario = "07:00",
    [string]$NomeTarefa = "pipeline-vendas",
    [switch]$Remover
)

if ($Remover) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
    Write-Host "Tarefa '$NomeTarefa' removida."
    return
}

$pastaProjeto = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python -ErrorAction Stop).Source

# roda dentro da pasta do projeto, porque os caminhos padrao (dados/entrada, saida) sao relativos
$acao = New-ScheduledTaskAction -Execute $python -Argument "-m vendas" -WorkingDirectory $pastaProjeto
$gatilho = New-ScheduledTaskTrigger -Daily -At $Horario
$config = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho -Settings $config `
    -Description "Roda o ETL de vendas das filiais e gera os CSVs para o Power BI" -Force | Out-Null

Write-Host "Tarefa '$NomeTarefa' criada: todo dia as $Horario."
Write-Host "Pasta do projeto: $pastaProjeto"
Write-Host "Para testar agora: Start-ScheduledTask -TaskName $NomeTarefa"
