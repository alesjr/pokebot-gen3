#diretriz

Esse arquivo é o handoff oficial da sessão anterior e deve ser tratado como fonte de verdade para:

* estado atual do trabalho;
* decisões já tomadas;
* investigações já concluídas;
* arquivos relevantes;
* pendências;
* critérios de aceite;
* estratégia para economia de tokens.

Continue exatamente da próxima pendência indicada no handoff, começando pelo RSE-029.

Regras obrigatórias:

* Não reanalise o repositório inteiro.
* Não repita investigações já documentadas no handoff.
* Não releia arquivos grandes sem necessidade.
* Leia apenas arquivos e trechos diretamente necessários para a tarefa atual.
* Prefira buscas específicas com `rg`.
* Evite `cat`, `sed` ou dumps extensos de arquivos completos.
* Não faça auditoria arquitetural fora do escopo.
* Não refatore código que não seja necessário para concluir a tarefa.
* Preserve as decisões arquiteturais existentes.
* Faça a menor alteração possível para atender ao requisito.
* Use o estado atual do worktree como autoridade.

Antes de alterar código:

1. Leia somente o handoff.
2. Identifique quais arquivos são realmente necessários para a pendência atual.
3. Leia apenas os trechos necessários desses arquivos.
4. Implemente a solução mais simples compatível com a arquitetura existente.

Testes:

* Execute primeiro apenas os testes diretamente relacionados à alteração.
* Corrija eventuais falhas.
* Só depois execute a regressão mais ampla definida no handoff.
* Não execute suítes completas repetidamente sem necessidade.

Ao concluir a tarefa:

* atualize este arquivo;
* marque o que foi concluído;
* registre arquivos alterados;
* registre testes executados e respectivos resultados;
* registre pendências ou riscos restantes;
* remova do handoff informações que não sejam mais úteis para a próxima sessão;
* deixe explícito qual é a próxima tarefa a executar.

IMPORTANTE: se uma informação já estiver registrada no handoff, não gaste contexto tentando confirmá-la novamente no repositório, salvo se houver evidência concreta de que o código atual contradiz o handoff.

Prioridade máxima: concluir corretamente a tarefa usando o mínimo possível de contexto e tokens.


# CONTINUAÇÃO — FLEET LIVING DEX GEN III

## Estado validado — 2026-08-22

RSE-004 a RSE-028 concluídos em Ruby, Sapphire e Emerald.

- RSE-021 fala com Dock no Stern's Shipyard e confirma `DOCK_REJECTED_DEVON_GOODS`;
- RSE-022 entra no Oceanic Museum, entrega Devon Goods, vence encontros pela engine central e confirma `DELIVERED_DEVON_GOODS`;
- RSE-023 cruza Route 110, vence rival pela engine central e confirma `ROUTE110_STATE > 0`;
- RSE-024 chega a Mauville e confirma `VISITED_MAUVILLE_CITY`;
- RSE-025 vence Wally pela engine central e confirma `DEFEATED_WALLY_MAUVILLE`;
- RSE-026 recebe HM06 pela engine normal e confirma item e flag específica da versão;
- RSE-027 resolve os layouts próprios de Mauville Gym, vence Wattson pela engine central e confirma `BADGE03_GET`;
- RSE-028 captura suporte HM não-shiny pela engine normal (Zigzagoon em RS, Marill em Emerald), ensina Rock Smash sem tocar no inicial, abre Rusturf Tunnel e recebe HM04;
- shiny e inicial são proibidos como usuários de HM;
- Sapphire treina Treecko/Grovyle legitimamente na Route 117 até nível 30 antes de Wattson;
- Sapphire treina Grovyle legitimamente até nível 20 em Granite Cave antes de Brawly;
- rotinas são idempotentes por flags/var persistentes;
- controle retorna e script global fica inativo no E2E;
- `LivingDexMode` executa RSE-021 a RSE-028 antes do loop principal;
- RSE-001 a RSE-020 permanecem cobertos pelo mesmo E2E.

Cura no Pokémon Center agora alterna `A/B`, observa fim real do script e possui
timeout explícito. Isso elimina hang intermitente visto no retorno da enfermeira
em Sapphire e transforma nova falha de script em erro recuperável/diagnosticável.
Blackouts durante navegação agora reobservam mapa real e reiniciam tentativa;
retomada dentro de Pokémon Center RSE sai do prédio antes de recalcular rota.

## Arquivos alterados neste marco

- `modules/living_dex/campaign_rse.py`
- `modules/modes/living_dex.py`
- `modules/modes/util/higher_level_actions.py`
- `tests/test_living_dex_intro.py`
- `docs/CODEX_CONTINUACAO_FLEET_LIVING_DEX_GEN3.md`

## Testes executados

- E2E RSE isolado, Ruby: verde, 1/1.
- E2E RSE isolado, Sapphire: verde, 1/1 após correção de cura.
- E2E final desde jogo novo, Ruby/Sapphire/Emerald: verde, 1/1 por jogo, incluindo RSE-028.
- regressão completa em Docker: **91/91 verde**.
- `git diff --check`: verde.

Avisos `Failed to initialise sound! Sound will be disabled.` esperados no container headless; sem impacto.
Nenhum risco funcional conhecido. Worktree continua sujo por trabalho acumulado; preservar.

## Próxima tarefa

RSE-029 — continuar campanha após Rusturf Tunnel.

Ainda não implementada. Não avançar para RSE-030 antes de RSE-029 passar
desde jogo novo em Ruby, Sapphire e Emerald.

Critério mínimo:

- definir objetivo/flags exatos da RSE-029 pelo documento de missões;
- executar progressão somente pela engine normal;
- recuperar controle e script global inativo;
- validar Ruby, Sapphire e Emerald;
- preservar 91 testes anteriores.

## Regras de continuação

- não reauditar RSE-001 a RSE-028;
- não reler arquivos grandes;
- usar `rtk rg` e trechos de 40–80 linhas;
- preservar worktree atual; não resetar mudanças;
- testes: focado → RSE E2E → regressão completa uma vez;
- nunca editar RNG, RAM, flags ou saves para fabricar progresso;
- perfis/saves atuais nunca apagar ou sobrescrever;
- remover `tests/rtc_anchor.json` após testes que o gerem.
