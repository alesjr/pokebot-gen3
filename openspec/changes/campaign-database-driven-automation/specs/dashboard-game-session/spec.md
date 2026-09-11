## Purpose

Define operação do emulador pelo dashboard mediante seleção de jogo, profile/save e modo, preservando jogo manual e automações existentes.

## ADDED Requirements

### Requirement: Seleção coerente de jogo e profile
O dashboard SHALL listar somente profiles associados ao jogo selecionado e SHALL iniciar exatamente o profile escolhido.

#### Scenario: Iniciar profile do jogo selecionado
- **WHEN** usuário seleciona um jogo, escolhe um profile listado e solicita início
- **THEN** aplicação inicia o emulador com ROM e save associados àquele profile

#### Scenario: Jogo sem profile
- **WHEN** usuário seleciona um jogo sem profiles existentes
- **THEN** dashboard informa ausência de profile e não inicia outro jogo implicitamente

### Requirement: Controle de modo pelo dashboard
O dashboard SHALL apresentar somente modos reais registrados pela aplicação e SHALL permitir alternar a instância ativa entre Manual, Campaign e demais modos selecionáveis.

#### Scenario: Jogar manualmente
- **WHEN** usuário seleciona Manual
- **THEN** bot interrompe automação e comandos manuais do dashboard controlam a instância ativa

#### Scenario: Iniciar Campaign
- **WHEN** usuário seleciona Campaign numa instância Ruby, Sapphire ou Emerald compatível
- **THEN** mesma instância começa a executar Campaign usando seu save atual

#### Scenario: Modo indisponível
- **WHEN** modo registrado não é selecionável no estado ou jogo atual
- **THEN** dashboard impede ativação e não substitui silenciosamente por outro modo

### Requirement: Estado operacional visível
O dashboard SHALL mostrar jogo, profile, modo, objetivo Campaign, imagem do emulador e atividade da instância usando estado real da aplicação.

#### Scenario: Acompanhar execução
- **WHEN** profile está ativo
- **THEN** dashboard atualiza imagem, modo, objetivo e atividade sem fabricar estado de missão

