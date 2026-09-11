## Context

Ver `proposal.md`. Dashboard e servidor web já controlam profile, modo, frames e comandos. `CampaignExecutor` já ordena etapas e avalia condições SQLite, porém `CampaignMode` mantém mapa manual de ações e ramificações de batalha por nome. Catálogo das três primeiras missões RSE ainda nasce em métodos Python. Projeto já possui modos e utilitários para starter, captura, treino, encontros únicos, batalha, navegação, cura, PC, HMs e leitura do save.

## Goals / Non-Goals

**Goals:**

- Preservar motor Campaign atual, tornando-o declarativo e extensível pelo catálogo.
- Reusar modos/controllers/funções existentes com mínimo código adaptador.
- Separar definição de missão, execução genérica e políticas globais.
- Manter conclusão derivada exclusivamente do save.
- Cobrir história principal de Ruby, Sapphire e Emerald com diferenças explícitas.

**Non-Goals:**

- Living Dex ou captura de toda espécie.
- FireRed/LeafGreen no Campaign desta mudança.
- Novo battle handler, battle policy ou loop de Pokémon Center.
- Framework web, banco adicional, container adicional ou dependência nova.
- Reescrita dos modos existentes.

## Decisions

### 1. Estender motor atual, não criar outro

`CampaignExecutor` continuará selecionando missão, avaliando condições e registrando observações. Alteração limitada: etapa carregará referência de capacidade e parâmetros; executor solicitará execução ao resolver genérico.

Alternativa rejeitada: novo workflow engine. Duplicaria loop, estado e listeners já existentes.

### 2. Catálogo versionado contém comportamento declarativo

Schema manterá missões, jogos, etapas e condições. Etapas ganharão parâmetros estruturados e, quando necessário, regra de recuperação. Dados de missão sairão de métodos `_seed_*` específicos e serão carregados como conteúdo SQL versionado pelo próprio módulo de missões. Python manterá somente schema, migração, leitura e execução genérica.

Regras globais serão armazenadas uma vez por jogo/escopo, não copiadas em cada missão. Valores incluem tamanho de time, critério de treino, reserva HM, política shiny e ação de encontro único.

Alternativa rejeitada: continuar adicionando funções `_seed_mission_n` e `if action == ...`; manteria Python como fonte real.

### 3. Resolver controlado equivalente a `eval`

Referência declarativa usará formato estável para função, controller ou mode interno. Resolver aceitará somente namespaces internos autorizados e tipos compatíveis com generators/modes. Parâmetros virão de JSON validado pelo catálogo. Nenhum texto externo será avaliado.

Modes serão localizados pelo registro existente sempre que possível. Funções internas terão referência módulo/símbolo. Referência inválida falhará antes de executar etapa.

Alternativa rejeitada: `eval()` cru. Mesmo flexível, permite execução arbitrária e dificulta validar catálogo.

### 4. Campaign delega ciclo de vida ao mode/controller ativo

Campaign guardará capacidade ativa e encaminhará callbacks já definidos pelo contrato de mode, incluindo início/fim de batalha, whiteout e evolução. Política global shiny roda antes da delegação. Assim `Starters`, `EV Train`, captura e resets mantêm comportamento próprio sem branches por nome de etapa.

Alternativa rejeitada: copiar lógica dos modes para Campaign ou criar segundo battle handler.

### 5. Estado do save decide progresso

Banco continuará aceitando somente estados operacionais (`locked`, `available`, `in_progress`) e observações. Seleção da próxima etapa sempre reavalia condições persistentes. Não será criada coluna `completed`.

Save states poderão servir como checkpoints técnicos, mas nunca como prova isolada de missão concluída.

### 6. Políticas globais envolvem etapas, não substituem capacidades

Antes de missão: avaliar composição, quantidade, saúde e nível-alvo. Durante encontros: shiny tem prioridade absoluta; batalha comum usa handler/estratégia existentes. Depois de captura ou quando reorganização for necessária: navegar ao centro apropriado usando localização salva, enum e busca existentes; operar PC pelo utilitário existente.

### 7. Seleção de combatentes ignora level

Somente Pokémon não shiny participam da seleção. Pontuação:

```text
combat_potential = sum(species.base_stats) + sum(pokemon.ivs)
```

Maior pontuação vence. Empate usa maior soma de IVs e depois identidade estável do Pokémon; level nunca entra na ordenação. Level permanece válido apenas para medir e cumprir alvo de treino definido pela missão.

### 8. HM Slayer usa cobertura, não força de combate

Para cada candidato não shiny, calcular conjunto de HMs requeridos que sua espécie pode aprender usando learnset existente. Selecionar combinação com menor número de Pokémon; dentro da mesma quantidade, maior cobertura individual e potencial de combate desempata. Preferência: um Pokémon cobrindo quatro HMs diferentes. Troca ocorre somente no PC e somente quando nova combinação melhora cobertura ou reduz vagas.

Requisitos temporários de equipe para eventos da história serão declarados pela missão e terão precedência somente durante aquela etapa.

### 9. Shinies ficam fora da equipe operacional

Interceptação Campaign solicita captura via estratégia existente. Se captura entrar numa vaga do time, Campaign agenda depósito antes de combate intencional seguinte. Se time estiver cheio, comportamento nativo envia captura ao PC. Sem bola ou espaço, automação pausa com erro explícito; não derrota nem abandona deliberadamente encontro.

Starter e encontros únicos usam seus modes existentes com condição shiny. Após primeira captura selvagem, starter shiny segue ao PC.

### 10. Dashboard permanece cliente fino

Dashboard lista ROMs, profiles e modes fornecidos pelo backend existente. Seleção inicia mesma aplicação/profile; troca de mode usa API atual. Nenhuma regra Campaign será duplicada em JavaScript.

## Risks / Trade-offs

- [Catálogo completo RSE possui muitas diferenças e flags] -> cadastrar por jogo e validar cada condição diretamente contra fontes já conhecidas do save.
- [Função interna muda de nome] -> resolver falha explicitamente; referências centralizadas no catálogo facilitam migração.
- [Mode interativo abre UI em headless] -> catálogo usa somente parâmetros não interativos já aceitos; capacidades sem entrada programática exigem menor extensão localizada no próprio mode.
- [Shiny surge sem recursos de captura] -> pausar preservando encontro; nunca aplicar fallback de luta/fuga.
- [Reorganização frequente custa navegação] -> executar somente em visita necessária ao PC ou quando requisito bloqueia próxima missão.
- [Pontuação simples não mede sinergia de golpes] -> regra solicitada permanece determinística: status base + IVs, sem level; estratégia de batalha continua escolhendo golpes.
- [Catálogo incorreto pode bloquear campanha] -> erros incluem missão, etapa, condição e referência responsáveis; save permanece fonte para retomada.

## Migration Plan

1. Evoluir schema sem apagar observações ou progresso operacional existente.
2. Converter três missões RSE atuais para catálogo declarativo versionado.
3. Substituir registro manual pelo resolver mantendo as mesmas condições de save.
4. Integrar políticas globais e composição usando capacidades existentes.
5. Expandir catálogo por ordem da história, separando variantes Ruby/Sapphire/Emerald.
6. Manter rollback por schema anterior e código anterior; saves/profiles não mudam de formato.
