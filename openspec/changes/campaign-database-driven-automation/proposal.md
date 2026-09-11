## Why

O dashboard já permite operar uma instância do emulador, mas o modo Campaign ainda mistura catálogo SQLite com ações e decisões específicas codificadas em Python. A campanha automática precisa ser dirigida pelo save e pelo banco, reutilizando modos, estratégias e utilitários existentes sem criar motores paralelos ou uma codebase extensa.

## What Changes

- Consolidar o dashboard como entrada para selecionar jogo, profile/save e modo, mantendo jogo manual e modos existentes disponíveis.
- Tornar o catálogo de missões fonte de verdade para ordem, condições, localização, ação reutilizável, parâmetros e conclusão das campanhas Ruby, Sapphire e Emerald.
- Resolver referências controladas a funções, controllers e modes internos existentes, com parâmetros vindos do catálogo, sem `eval()` arbitrário nem mapas crescentes de handlers por missão.
- Derivar conclusão exclusivamente do estado real do save; persistir no banco somente execução e observações operacionais.
- Aplicar regras globais Campaign para captura obrigatória de shinies, starter shiny, primeira captura selvagem, preenchimento do time, treino preventivo, composição do time, HM Slayer e encontros únicos/lendários shiny.
- Avaliar combatentes não shiny pelo potencial composto por status base e IVs; nunca usar level na seleção do melhor combatente. Level permanece somente como medida do requisito de treino da missão.
- Reutilizar `StartersMode`, `CatchStrategy`, `EVTrainMode`, controllers de encontros únicos, navegação, cura, PC e leitura de save existentes.
- Não implementar Living Dex, nova battle policy, novo battle handler ou loop paralelo de Pokémon Center.

## Capabilities

### New Capabilities

- `dashboard-game-session`: Seleção e operação de jogo, profile/save e modo pelo dashboard, incluindo controle manual e inicialização do Campaign.
- `database-driven-campaign`: Execução integral das campanhas RSE orientada pelo catálogo e save, com despacho de capacidades existentes e regras globais de captura, treino e equipe.

### Modified Capabilities

Nenhuma. O projeto ainda não possui specs OpenSpec publicadas.

## Impact

- Catálogo e schema em `modules/missions/` e banco SQLite de missões.
- Orquestração em `modules/campaign/` e `modules/modes/campaign.py`.
- Integração, sem duplicação, com modes, batalha, encontro, navegação, cura, PC, Pokémon e save existentes.
- Estado e comandos expostos pelo servidor e frontend do dashboard existentes.
- Sem novo framework web, banco, container, dependência ou sistema de testes.
