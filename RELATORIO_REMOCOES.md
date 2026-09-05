# Relatório de remoções e alinhamento com `main`

Data: 2026-09-03

## Escopo aplicado

- Remover arquivo criado fora da `main`, sem uso e fora das features Dashboard/Campaign.
- Remover implementação paralela quando a `main` já possui mecanismo equivalente.
- Preservar arquivos usados por Dashboard ou Campaign e documentá-los para revisão.
- Não alterar Dashboard durante esta limpeza.
- Não alterar mudanças do usuário ou arquivos sem autoria confirmada.

## Arquivos removidos

### `modules/campaign/battle_policy.py`

Removido por criar um sistema paralelo para batalha, cura e recuperação de whiteout.

Funcionalidades duplicadas ou sobrepostas existentes na `main`:

- despacho de batalha: `modules/modes/_listeners.py` e `modules/battle_handler.py`;
- decisão de encontro/captura: `modules/encounter.py::handle_encounter`;
- estratégias: `modules/battle_strategies/`;
- loop de cura existente: `modules/modes/util/pokecenter_loop.py`;
- busca de Centro Pokémon: `modules/modes/util/map.py::find_closest_pokemon_center`;
- cura: `modules/modes/util/higher_level_actions.py::heal_in_pokemon_center`;
- último local de cura: `modules/save_data.py::get_last_heal_location`.

Remoções relacionadas:

- import e instância de `CampaignBattlePolicyController` no modo Campaign;
- callbacks paralelos de batalha e whiteout;
- wrappers `run_guarded()` em navegação, cura e depósito;
- leitura/configuração de policy por missão;
- `MissionBattlePolicy` e método `battle_policy()`;
- seed da policy na missão 3;
- tabela `mission_battle_policies`.

### `utility/init_missions_database.py`

Removido por não possuir chamada, import ou entrada operacional. `MissionsDatabase.initialize_builtin_catalog()` já é chamado pelo Campaign e backend do Dashboard.

## Arquivo original restaurado

### `modules/modes/util/pokecenter_loop.py`

Arquivo não foi removido: pertence à `main` e é usado por:

- `modules/modes/level_grind.py`;
- `modules/modes/item_steal.py`.

Foram removidas somente 20 linhas adicionadas fora da `main`:

- `healing_requested`;
- `returning_from_whiteout`;
- `clear_healing_request()`;
- `request_healing_if_party_cannot_battle()`;
- `request_healing()`.

Resultado: arquivo voltou ao comportamento da `main`.

## Banco de missões

`modules/missions/database.py` foi limpo da battle policy. Schema passou para versão 6 somente para migrar bancos existentes:

1. aceita schema antigo 3, 4 ou 5;
2. executa `DROP TABLE IF EXISTS mission_battle_policies`;
3. grava schema 6.

Banco novo não cria tabela de battle policy. Nenhuma regra paralela permanece no catálogo.

## Campaign após limpeza

`modules/modes/campaign.py` voltou a chamar diretamente funções de `modules/campaign/rse.py`, sem controlador paralelo.

Captura/cura da missão 3 foi marcada como `TODO` em `run_catch_new_route102_pokemon()`. Quando alvo ainda não foi cumprido, Campaign para com erro explícito. Motivo: impedir nova automação improvisada antes de integrar corretamente:

- battle handler original;
- `handle_encounter()`;
- `get_last_heal_location()`;
- enum `PokemonCenter`;
- busca de centro mais próximo.

## Arquivos fora da `main` preservados por uso real

### Campaign

- `modules/campaign/__init__.py`: exporta executor e leitor usados por `modules/modes/campaign.py`.
- `modules/campaign/engine.py`: executa passos e condições do catálogo; usado pelo modo Campaign.
- `modules/campaign/rse.py`: ações RSE registradas pelo modo Campaign.
- `modules/missions/__init__.py`: exporta banco usado por Campaign e Dashboard.
- `modules/missions/database.py`: catálogo e progresso orientados pelo save; usado por Campaign e Dashboard.
- `modules/modes/campaign.py`: modo selecionável da feature Campaign.

Reuso e pontos para revisão:

- `run_choose_starter()` foi removido. Campaign instancia `StartersMode` com starter configurado e delega seu callback e gerador ao modo original.
- `StartersMode` recebeu somente dois parâmetros opcionais: escolha programática e parada ao encontrar shiny. Instâncias normais preservam comportamento anterior.
- alcance da bolsa e finalização do starter foram movidos de `campaign/rse.py` para `modules/modes/starters.py`.
- `run_clock_setup()` foi removido de `campaign/rse.py`. Controle e alcance do relógio agora pertencem a `modules/clock.py`.
- `_player_house_maps()` foi removido de `campaign/rse.py`. Mapeamento da casa do player agora pertence a `modules/player.py::get_player_house_maps()` e é reutilizado pelo Campaign.
- `run_heal_captured_pokemon()` foi removido; Campaign resolve o enum do catálogo e chama `heal_in_pokemon_center()` diretamente.
- `run_ev_train_captured_pokemon()` foi removido; Campaign chama `EVTrainMode.run_until_party_level()` diretamente.
- Demais ações `run_*` RSE não possuem função homônima na `main`; orquestram navegação, memória e interação existentes.

## Auditoria de `modules/campaign/rse.py`

| Função original | Resultado | Destino/motivo |
|---|---|---|
| `run_new_game_intro()` | mantida | ação narrativa exclusiva da Campaign RSE; reutiliza teclado e estado do player |
| `_current_map()` | removida | substituída por `player.py::get_player_location()` |
| `_wait_for_control()` | removida | opções incorporadas em `walking.py::wait_for_player_avatar_to_be_controllable()` |
| `_walk_through_warp()` | movida | `walking.py::walk_through_warp()` |
| `run_reach_bedroom_clock()` | movida | `clock.py::reach_bedroom_clock()` |
| `run_meet_rival()` | mantida | ação narrativa exclusiva da Campaign RSE |
| `run_reach_starter_bag()` | movida | `starters.py::reach_rse_starter_bag()` |
| `_advance_until_lab_prompt()` | movida | helper privado de `starters.py` |
| `_finish_starter_lab()` | movida | helper privado de `starters.py` |
| `_save_campaign_checkpoint()` | movida | `campaign/engine.py::save_campaign_checkpoint()` |
| `run_finish_starter_sequence()` | movida | `starters.py::finish_rse_starter_sequence()`; checkpoint ficou no Campaign |
| `run_defeat_route103_rival()` | mantida | ação narrativa/batalha exclusiva da Campaign RSE |
| `run_receive_first_poke_balls()` | mantida | ação narrativa exclusiva da Campaign RSE |
| `run_leave_birch_lab()` | mantida | transição específica da sequência RSE |
| `run_navigate_to_catalog_location()` | movida | `campaign/engine.py::navigate_to_catalog_location()` |
| `run_reach_route102()` | removida | wrapper desnecessário; Campaign chama navegação + checkpoint diretamente |
| `run_catch_new_route102_pokemon()` | mantida como `TODO` | ação específica da missão 3, sem implementação paralela |
| `run_heal_captured_pokemon()` | removida | Campaign chama mecanismo original de cura diretamente |
| `run_deposit_shiny_starter()` | mantida | orquestração específica da missão 3; depósito real delegado a `pc_interaction.py` |
| `run_ev_train_captured_pokemon()` | removida | wrapper desnecessário; Campaign chama `EVTrainMode` diretamente |

### Extensão usada em arquivo da `main`

- `modules/modes/ev_train.py::run_until_party_level()`: permanece porque `modules/modes/campaign.py` chama essa função. Também permanecem suporte a `_level_target`, rotação do lead e tratamento de party sem Pokémon apto. Não cria novo modo de batalha; reutiliza `EVTrainMode`, `handle_encounter()`, estratégia existente e cura existente.

Esta reorganização foi apenas inspecionada estaticamente. Nenhum teste, build, Docker, import de validação ou execução da aplicação foi realizado.

### RNG manipulation

- `modules/rng_manipulation.py`: preservado porque foi solicitado como feature e `modules/modes/util/soft_reset.py` usa `wait_for_unique_rng_value()`.
- Busca encontrou leitura isolada de `gRngValue` na UI de debug, mas nenhuma função original equivalente para calcular/avançar RNG e manter histórico por profile.

### Dashboard

- `modules/web/instance_server.py`: importado por `modules/main.py`; backend da instância web.
- `modules/web/log_buffer.py`: importado por `modules/console.py` e `modules/web/instance_server.py`; espelha logs reais no Dashboard.
- `dashboard_layout_reference.png`: referência fornecida para Dashboard.

Esses arquivos ficaram intactos nesta limpeza.

## Arquivos fora da `main` preservados por não pertencerem à limpeza

- `.env`: configuração local usada pela execução Docker.
- `AGENTS.md`: instruções do projeto.
- `corrigir a ia burra depois`: autoria/uso não confirmados; preservado para não apagar arquivo do usuário.
- `RELATORIO_REMOCOES.md`: este relatório, solicitado pelo usuário.

## Validação executada

- Busca global: nenhuma importação ou chamada restante de `CampaignBattlePolicyController`, `MissionBattlePolicy` ou `battle_policy()`.
- `pokecenter_loop.py`: sem diferença funcional contra `main`.
- `git diff --check`: sem erro de whitespace.
- Compilação Python dos arquivos Campaign, missões, Dashboard, RNG e modos alterados: concluída sem erro.
- Imagem Docker reconstruída e container único da aplicação iniciado com estado `healthy`.
- Banco ativo migrado para schema 6; consulta confirmou zero tabelas chamadas `mission_battle_policies`.
