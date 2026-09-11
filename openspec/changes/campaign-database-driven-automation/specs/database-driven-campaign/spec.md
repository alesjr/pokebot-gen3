## Purpose

Define execução automática das campanhas Ruby, Sapphire e Emerald por catálogo persistente, estado real do save e capacidades já existentes do bot.

## ADDED Requirements

### Requirement: Catálogo como fonte de verdade
O Campaign SHALL obter do banco a ordem das missões, jogos aplicáveis, pré-requisitos, condições de início, localizações, ações, parâmetros, regras de recuperação e critérios de conclusão. Diferenças entre Ruby, Sapphire e Emerald MUST estar representadas no catálogo.

#### Scenario: Selecionar próxima missão
- **WHEN** Campaign lê um save RSE
- **THEN** próxima missão é a primeira entrada aplicável cuja condição final ainda não é comprovada pelo save

#### Scenario: Fluxo diferente entre versões
- **WHEN** mesma etapa possui diferença entre Ruby, Sapphire e Emerald
- **THEN** Campaign usa registro específico do jogo informado pelo profile

### Requirement: Conclusão derivada do save
O Campaign SHALL considerar missão concluída somente quando condições persistentes do cartucho/save forem satisfeitas. Banco de missões MUST NOT armazenar conclusão como verdade independente do save.

#### Scenario: Reiniciar aplicação
- **WHEN** aplicação reinicia durante missão
- **THEN** Campaign relê o save, ignora observação operacional obsoleta e retoma primeira etapa ainda não comprovada

#### Scenario: Progresso operacional divergente
- **WHEN** banco indica etapa anteriormente executada mas save não comprova sua conclusão
- **THEN** Campaign trata etapa como pendente

### Requirement: Despacho controlado de capacidades existentes
O catálogo SHALL referenciar funções, controllers ou modes internos conhecidos com parâmetros declarativos. Executor SHALL rejeitar referências fora da lista interna permitida e SHALL reutilizar capacidades existentes em vez de duplicar comportamento.

#### Scenario: Executar mode cadastrado
- **WHEN** etapa referencia mode interno permitido com parâmetros válidos
- **THEN** Campaign executa esse mode e encaminha seus eventos de batalha até a condição de conclusão ser satisfeita

#### Scenario: Referência não permitida
- **WHEN** catálogo contém referência não reconhecida ou externa ao conjunto permitido
- **THEN** Campaign interrompe etapa com erro explícito sem executar conteúdo arbitrário

### Requirement: Starter obrigatoriamente shiny
O Campaign SHALL obter o starter configurado por soft reset usando o mode de starters existente e SHALL prosseguir somente após o save possuir esse starter shiny.

#### Scenario: Starter normal
- **WHEN** starter obtido não é shiny
- **THEN** Campaign reinicia tentativa conforme mode existente

#### Scenario: Starter shiny confirmado
- **WHEN** starter configurado é shiny e está persistido no save
- **THEN** Campaign conclui requisito e prossegue

### Requirement: Captura prioritária de todo shiny
Durante Campaign, todo encontro shiny capturável SHALL receber prioridade sobre luta, fuga, treino ou regra comum de captura. Todo shiny capturado SHALL ser armazenado no PC e MUST NOT integrar equipe de combate.

#### Scenario: Shiny durante navegação ou treino
- **WHEN** encontro selvagem shiny começa durante qualquer etapa Campaign
- **THEN** bot usa estratégia de captura existente e agenda armazenamento no PC

#### Scenario: Shiny capturado entra no time
- **WHEN** jogo coloca shiny capturado numa vaga livre do time
- **THEN** Campaign o deposita no PC na primeira visita segura necessária antes de usá-lo em combate

#### Scenario: Captura impossível
- **WHEN** faltam Poké Balls ou espaço de armazenamento para capturar shiny
- **THEN** Campaign interrompe automação com motivo explícito em vez de derrotar ou abandonar deliberadamente o shiny

### Requirement: Primeira captura após obter Poké Balls
O primeiro encontro selvagem após o save registrar posse inicial de Poké Balls SHALL ser capturado usando estratégia existente, independentemente de espécie normal já vista. Após captura, starter shiny SHALL ser depositado no PC.

#### Scenario: Primeiro encontro elegível
- **WHEN** jogador possui Poké Ball e ainda não existe evidência da primeira captura Campaign
- **THEN** próximo encontro selvagem usa estratégia de captura

#### Scenario: Starter após primeira captura
- **WHEN** primeira captura é comprovada no save
- **THEN** Campaign cura quando necessário, acessa PC por navegação existente e deposita starter shiny

### Requirement: Time preenchido até seis
O Campaign SHALL capturar Pokémon quando permitido até manter seis integrantes ativos, respeitando armazenamento obrigatório de shinies, vaga mínima de HM Slayer e requisitos temporários cadastrados pela missão.

#### Scenario: Time incompleto
- **WHEN** time possui menos de seis integrantes e recursos de captura estão disponíveis
- **THEN** Campaign usa rotina e estratégia de captura existentes até preencher as vagas

#### Scenario: Captura shiny durante preenchimento
- **WHEN** shiny é capturado enquanto time está sendo preenchido
- **THEN** shiny é armazenado e não satisfaz permanentemente vaga de combatente

### Requirement: Treino antes de missões
Antes de iniciar missão, Campaign SHALL comparar níveis atuais com nível-alvo definido no catálogo e SHALL usar modo de treino existente para elevar integrantes combatentes abaixo desse alvo. Level SHALL ser usado somente nessa verificação de treino, nunca para selecionar melhor combatente.

#### Scenario: Integrante abaixo do alvo
- **WHEN** combatente necessário está abaixo do nível-alvo da missão
- **THEN** Campaign treina e cura usando capacidades existentes antes de iniciar missão

#### Scenario: Equipe no nível requerido
- **WHEN** todos os combatentes necessários atingem nível-alvo
- **THEN** Campaign inicia missão sem treino adicional

### Requirement: Composição por potencial e IVs
Ao acessar PC, Campaign SHALL comparar Pokémon não shiny do time e armazenamento. Pontuação de combate SHALL ser composta pela soma dos status base da espécie com a soma dos IVs individuais. Level MUST NOT participar da pontuação ou desempate. Pokémon shiny MUST NOT ser selecionado como combatente.

#### Scenario: Pokémon de nível maior e potencial menor
- **WHEN** Pokémon possui level maior mas pontuação de status base mais IVs é menor
- **THEN** Campaign prefere Pokémon de maior potencial independentemente do level

#### Scenario: Shiny com maior pontuação
- **WHEN** shiny possui maior pontuação que candidatos normais
- **THEN** Campaign mantém shiny no PC e seleciona melhor candidato não shiny

#### Scenario: Reorganização no PC
- **WHEN** armazenamento contém candidato normal com pontuação superior a combatente atual
- **THEN** Campaign troca ambos usando interação de PC existente

### Requirement: HM Slayer mínimo
O time SHALL reservar o menor número possível de vagas para cobrir HMs exigidos pelo progresso atual, preferindo um único Pokémon capaz de aprender quatro HMs diferentes. Candidato SHALL ser substituído quando outro não shiny oferecer cobertura HM estritamente melhor.

#### Scenario: Um candidato cobre quatro HMs
- **WHEN** Pokémon não shiny disponível pode aprender quatro HMs requeridos
- **THEN** Campaign o prioriza como único HM Slayer

#### Scenario: Cobertura superior encontrada
- **WHEN** novo candidato não shiny cobre mais HMs requeridos que HM Slayer atual
- **THEN** Campaign substitui HM Slayer na próxima reorganização segura no PC

#### Scenario: Um HM Slayer insuficiente
- **WHEN** nenhum único Pokémon cobre todos os HMs atualmente obrigatórios
- **THEN** Campaign usa quantidade mínima de especialistas necessária para cobrir requisitos cadastrados

### Requirement: Encontros únicos e lendários shiny
Encontros únicos ou lendários marcados no catálogo SHALL usar mode correspondente já existente e SHALL ser aceitos somente quando shiny, salvo encontro explicitamente não shiny-lockado pelo catálogo por regra do jogo.

#### Scenario: Lendário permite shiny
- **WHEN** missão alcança encontro lendário que pode ser shiny
- **THEN** Campaign usa rotina de reset correspondente até capturar versão shiny

#### Scenario: Tipo de encontro diferente
- **WHEN** encontro é estático, presente, roamer ou outro tipo suportado
- **THEN** catálogo seleciona mode existente adequado ao tipo

### Requirement: Batalha e cura durante percurso
Encontros e treinadores inevitáveis durante navegação SHALL usar battle handler e estratégia configurada existentes. Campaign SHALL curar usando localização de cura salva e busca de centro existente antes de arriscar whiteout; após derrota, SHALL reavaliar treino antes de prosseguir.

#### Scenario: Batalha incidental vencível
- **WHEN** batalha selvagem ou de treinador interrompe percurso
- **THEN** bot luta usando estratégia configurada e retoma etapa após vitória

#### Scenario: Equipe sem segurança para prosseguir
- **WHEN** estado da equipe indica risco de todos desmaiarem
- **THEN** Campaign interrompe percurso, cura ou treina usando capacidades existentes e só depois retoma

#### Scenario: Whiteout ocorrido
- **WHEN** equipe inteira desmaia
- **THEN** Campaign reconhece retorno ao último ponto de cura, reavalia nível requerido e não repete confronto antes da preparação

### Requirement: Escopo de captura não é Living Dex
O Campaign MUST NOT perseguir conclusão de Pokédex ou coleção Living Dex. Capturas normais SHALL ocorrer somente para preencher equipe, cumprir missão ou requisito explicitamente cadastrado.

#### Scenario: Time completo sem requisito de captura
- **WHEN** time atende composição e missão não exige captura
- **THEN** Campaign não captura espécie apenas por ainda não possuí-la

