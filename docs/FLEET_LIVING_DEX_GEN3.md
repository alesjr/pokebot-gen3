# Frota Living Dex Gen III

Status: planejamento futuro. Nada descrito aqui deve ser anunciado como
funcional antes dos critérios de aceite serem cumpridos.

## Objetivo

Executar Pokémon Ruby, Sapphire, Emerald, FireRed e LeafGreen simultaneamente,
desde novos jogos, sob um coordenador único. Cada jogo continua isolado em seu
perfil, enquanto a coleção e o dashboard apresentam uma National Living Dex
conjunta.

Resultado esperado:

- cinco campanhas autônomas, incluindo ginásios, HMs, Elite Four e pós-jogo;
- 385 espécies shiny e um Celebi oficial normal;
- macho e fêmea quando ambos existem;
- 28 formas de Unown e demais formas armazenáveis;
- formas de Deoxys dependentes do jogo;
- exclusão de padrões infinitos de Spinda e formas temporárias de batalha;
- trocas e distribuições realizadas por protocolos emulados, sem criar
  Pokémon ou editar diretamente RNG, RAM, event flags ou saves.

Celebi shiny não teve obtenção oficial na Geração III; Celebi normal será a
única exceção da meta shiny. Mew shiny legítimo exige Pokémon Emerald japonês
e Old Sea Map. Referências: [Faraway Island][faraway-island] e
[pesquisa sobre shiny locks da Geração III][gen3-shiny-locks].

## Decisões fixadas

| Tema | Decisão |
|---|---|
| Treinador | `Alesjr`, masculino, em todos os perfis |
| Coleção | uma National Living Dex compartilhada |
| Qualidade | todos shiny, exceto Celebi oficial normal |
| Dashboard | central e individual, somente leitura |
| Vídeo | MJPEG adaptativo, 15 FPS |
| Execução | cinco instâncias Docker headless |
| Trocas | link cable emulado, sem modificação direta de save |
| Eventos | assets oficiais fornecidos pelo usuário |
| Duplicatas shiny | nunca liberar; pausar e alertar quando faltar espaço |
| Perfis auxiliares | permitidos e automatizados |
| Áudio | desligado |

Os cinco saves principais devem usar perfis novos. Perfis atuais nunca serão
apagados, reiniciados ou sobrescritos. Nomes previstos:

- `LivingDex-Ruby`;
- `LivingDex-Sapphire`;
- `LivingDex-Emerald`;
- `LivingDex-FireRed`;
- `LivingDex-LeafGreen`.

Perfis auxiliares cobrem starters faltantes, fósseis, recompensas únicas e
eventos. Depois de uma troca confirmada, o perfil auxiliar pode ser arquivado,
mas não apagado automaticamente.

## Interfaces planejadas

### Configuração

Criar `fleet.yml` com:

- identidade do treinador;
- perfil, ROM, starter, porta e prioridade de cada jogo;
- porta do dashboard central;
- FPS e qualidade JPEG;
- políticas de shiny, formas, duplicatas, eventos e recuperação;
- caminhos dos manifests de distribuição;
- segredo interno gerado localmente para comunicação entre serviços.

Distribuição inicial de starters:

| Perfil | Starter | Porta |
|---|---|---:|
| Ruby | Mudkip | 8888 |
| Sapphire | Treecko | 8889 |
| Emerald | Torchic | 8890 |
| FireRed | Charmander | 8891 |
| LeafGreen | Squirtle | 8892 |

Bulbasaur e outros one-offs virão de perfis auxiliares ou breeding depois de
troca legítima.

### CLI

Adicionar sem quebrar comandos individuais existentes:

```sh
sh pokebot-docker.sh start-all
sh pokebot-docker.sh stop-all
sh pokebot-docker.sh status-all
sh pokebot-docker.sh logs-all
```

`start-all` deve validar ROMs, portas, configuração e propriedade dos perfis
antes de iniciar qualquer instância. Porta ocupada ou perfil já aberto causa
falha segura; o comando nunca encerra processo externo automaticamente.

### Modos e HTTP

- criar modo `Living Dex Gen III` para RSE e FRLG;
- manter `Living Dex RSE` como alias compatível durante migração;
- dashboard central em `http://localhost:8877/`;
- dashboards individuais em `http://localhost:8888/` até `:8892/`;
- manter `GET /dashboard/state`;
- adicionar `GET /dashboard/video.mjpeg`;
- adicionar `GET /fleet/state`;
- adicionar `GET /fleet/instances/{profile}`;
- adicionar `GET /fleet/video/{profile}`.

Todas as rotas públicas permanecem somente leitura. Comandos internos do
coordenador usam rede Docker privada, token local e não publicam portas.

## Arquitetura

### Coordenador da frota

Um serviço `fleet-coordinator` será o único escritor de um banco SQLite
compartilhado. Responsabilidades:

- registrar heartbeats e estado das cinco instâncias;
- calcular próximo objetivo global;
- atribuir caças conforme versão, local e método de obtenção;
- registrar espécimes por PID, espécie, OT, TID/SID, perfil, gênero e forma;
- controlar checkpoints, leases, trocas, eventos e bloqueios;
- agregar estado para dashboard central;
- reconciliar party e boxes depois de todo reinício.

Antes do coordenador global existir, cada perfil reutiliza seu `stats.db` para
persistir o catálogo importado das docs, relação missão/flag e último valor
observado de cada flag. A migração deve preservar tabelas de encontros.

Somente uma instância pode possuir lease de escrita de um perfil. Bot normal,
trade worker e distribution worker nunca acessam o mesmo save simultaneamente.

### Vídeo web

O dashboard exibirá o framebuffer do GBA, não a interface desktop Tk.

Fluxo obrigatório:

1. assinante conecta ao stream MJPEG;
2. capturador pede renderização do próximo frame natural;
3. loop principal executa esse frame normalmente;
4. framebuffer 240×160 é copiado;
5. renderização volta a ficar desligada;
6. thread dedicada codifica JPEG e publica frame mais recente.

Captura não pode executar frame extra, criar/carregar save state, alterar
inputs ou fazer reset. Uma fila de tamanho um descarta frames atrasados. Todos
os espectadores compartilham o mesmo JPEG. Sem assinantes, custo de captura
deve ser zero. Aba oculta encerra stream e reconecta quando voltar a ficar
visível.

Dashboard central mostra cinco cards com tela, objetivo, velocidade, resets,
encontros, alertas e atividade. Clique abre dashboard individual. Falha de uma
instância marca somente seu card offline.

### Motor de campanha

Substituir fluxo monolítico por grafo declarativo de quests. Cada nó define:

- pré-condições por flags, mapa, inventário, party e boxes;
- ação: navegar, conversar, batalhar, curar, comprar, usar HM, resolver
  puzzle, capturar, criar egg, evoluir, trocar ou salvar;
- condição verificável de conclusão;
- checkpoint seguro e estratégia de retomada;
- limite de tentativas e motivo de bloqueio.

Manter conjuntos separados para Ruby/Sapphire, Emerald e FireRed/LeafGreen.
Automatizar intro, nome, gênero, relógio RSE, starter shiny, campanha,
ginásios, HMs, Elite Four, National Dex e pós-jogo.

Ao iniciar ou recuperar, estado real do cartucho é autoridade. O bot consulta
flags, mapa, inventário, party e storage; `living_dex_progress.json` serve como
histórico, não como prova exclusiva de conclusão.

### Planejador da Living Dex

Criar matriz de obtenção por versão, mapa e método. O planejador deve:

- escolher jogo com melhor acesso para cada alvo;
- calcular quantidade shiny necessária por família evolutiva;
- preservar uma cópia de cada estágio;
- caçar ambos os gêneros quando disponíveis;
- controlar 28 Unown e formas persistentes;
- tratar Wurmple, Tyrogue, Eevee, Nincada/Shedinja e Clamperl;
- tratar Safari, Feebas, gifts, roamers e encontros estáticos;
- usar breeding quando melhor ou obrigatório;
- salvar imediatamente depois de toda captura única.

Entre duas missões, cada rota intermediária funciona como barreira de hunting.
O bot enfrenta encontros para ganhar experiência e capturar alvos shiny da
rota. Ele somente segue para a próxima missão quando não restar alvo shiny
planejado e a equipe utilizável atingir o nível mínimo definido para o próximo
chefe ou desafio. Atingir o nível antes dos shinies não encerra a caça.

Lendários e outros encontros únicos somente contam quando shiny. Depois da
captura, save dentro do jogo deve terminar antes de qualquer novo reset.

### Link cable e eventos

Trade worker recebe leases exclusivos de dois perfis parados. Sequência:

1. ambos salvam dentro do jogo;
2. containers normais param e liberam arquivos;
3. snapshots transacionais dos dois perfis são criados;
4. worker carrega dois cores mGBA e conecta SIO em lockstep;
5. menus do Trade Center são automatizados;
6. espécies e identidades recebidas são verificadas;
7. ambos salvam dentro do jogo;
8. worker encerra, leases são liberados e bots reiniciam.

Falha em qualquer etapa restaura os dois snapshots byte a byte. Nunca restaurar
apenas um lado.

Assets de evento ficam fora do Git. Manifest registra SHA-256, região, jogo e
evento. Distribution worker reproduz protocolo oficial emulado; não injeta
Pokémon diretamente. Asset ausente gera `blocked_event_asset`, sem parar outras
campanhas ou caças.

## Persistência e proteção de saves

- save dentro do jogo antes de reset, troca, evento ou mudança de dono;
- confirmação do fim da escrita antes de registrar checkpoint;
- snapshots criados somente com processo dono parado;
- gravação atômica de progresso e banco;
- backups com retenção documentada;
- nenhuma escrita direta em RNG, RAM, Pokémon ou event flags;
- falha desconhecida pausa somente instância afetada;
- duplicata shiny nunca é liberada automaticamente;
- box sem espaço pausa caça antes de nova captura e publica alerta;
- migração importa progresso reconhecido sem remover arquivo original.

## Marcos de implementação

1. **Vídeo seguro:** capturador, MJPEG, dashboard individual e medição de
   impacto.
2. **Frota:** coordenador, SQLite, leases, rede privada, dashboard central e
   comandos `*-all`.
3. **Campanhas:** motor declarativo, novo jogo completo RSE, depois FRLG.
4. **Coleção:** matriz global, breeding, evoluções, variantes e storage.
5. **Trocas:** SIO lockstep, worker transacional e perfis auxiliares.
6. **Eventos:** manifests, distribution worker, Japanese Emerald, Mew, Jirachi
   e Celebi.
7. **Endurance:** recuperação, performance, execução longa e documentação
   operacional.

Entrega pode usar commits incrementais, mas `start-all` não deve ser declarado
pronto antes dos marcos obrigatórios passarem.

## Testes

### Unitários

- grafos sem ciclos ou marcos inalcançáveis;
- matriz cobre todas as espécies, gêneros e formas exigidas;
- regra 385 shiny + Celebi oficial normal;
- reconciliação idempotente depois de restart;
- captura de vídeo não altera frame, RNG, input ou save state;
- backpressure do encoder não bloqueia emulação;
- lease impede dupla escrita.

### Integração

- intro e principais marcos de RSE e FRLG;
- starter, estáticos, roamers, breeding e evoluções especiais;
- retomada em diálogo, batalha, save e soft reset;
- troca real entre dois perfis descartáveis;
- falha injetada em cada fase da troca restaura ambos os saves;
- evento com asset válido, inválido e ausente.

### Docker e performance

- cinco instâncias e coordenador simultâneos;
- portas, projects e volumes isolados;
- restart de um jogo não afeta outros;
- dashboard central e individual entregam 15 FPS;
- sem espectadores, captura fica inativa;
- com cinco streams, perda de throughput alvo limitada a 20% na máquina de
  referência Ryzen 7 7700X.

## Critérios de aceite

- `start-all` inicia frota nova sem tocar perfis antigos;
- cinco jogos avançam autonomamente desde novo jogo;
- progresso conjunto sobrevive a restart total;
- cada captura shiny aparece uma vez no inventário global;
- saves continuam recuperáveis depois de falhas simuladas;
- trocas não permitem acesso concorrente ao mesmo perfil;
- eventos ausentes geram bloqueio explicável, não corrupção;
- dashboards funcionam sem X11 e sem rotas públicas de controle;
- nenhuma ROM, save, dump ou segredo entra no repositório.

## Riscos

- binding SIO atual é baixo nível; lockstep exige protótipo e testes de
  timing antes das trocas reais;
- automação integral de cinco campanhas exige grande cobertura de mapas,
  scripts e recuperação;
- caça full odds pode durar muito mesmo sem throttle;
- distribuições dependem de assets oficiais compatíveis fornecidos pelo
  usuário;
- 15 FPS em cinco telas aumenta CPU; stream adaptativo e descarte de frames são
  obrigatórios;
- formas/gêneros aumentam uso de boxes e chance de bloqueio por capacidade.

[faraway-island]: https://bulbapedia.bulbagarden.net/wiki/Faraway_Island
[gen3-shiny-locks]: https://projectpokemon.org/home/forums/topic/59663-shiny-locked-pok%C3%A9mon-gen-iii/
