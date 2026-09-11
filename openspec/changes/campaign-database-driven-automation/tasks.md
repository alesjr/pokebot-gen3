## 1. Catálogo e persistência

- [x] 1.1 Evoluir schema existente para parâmetros declarativos de ação, recuperação e regras globais por jogo; confirmar por inspeção que progresso continua sem estado `completed`
- [x] 1.2 Mover dados das três missões RSE atuais dos métodos Python específicos para catálogo SQL versionado; confirmar que cada linha mantém jogo, ordem, localização, condições e ação equivalentes
- [x] 1.3 Carregar ações, parâmetros e regras globais nos modelos de leitura existentes; confirmar que plano retornado pelo banco contém todos os campos necessários sem regra de missão embutida no leitor
- [x] 1.4 Remover seeds e correções incrementais obsoletas somente após representação equivalente no catálogo; confirmar ausência de definições duplicadas para mesma missão

## 2. Despacho e delegação Campaign

- [x] 2.1 Implementar resolver controlado para referências internas de função, controller e mode, reutilizando registro de modes; confirmar rejeição explícita de namespace, símbolo ou parâmetros não permitidos
- [x] 2.2 Adaptar executor atual para invocar capacidade resolvida com parâmetros do catálogo; confirmar que execução ainda reavalia condições do save antes e depois da ação
- [x] 2.3 Encaminhar callbacks Campaign para capacidade ativa pelo contrato existente de mode; confirmar suporte a batalha iniciada/finalizada, whiteout e evolução sem branches pelo nome da etapa
- [x] 2.4 Remover mapa manual e wrappers Campaign que apenas duplicam chamadas existentes; confirmar que ações das três missões convertidas resolvem diretamente para capacidades reais

## 3. Políticas globais de encontro e captura

- [x] 3.1 Integrar prioridade shiny no callback Campaign antes da capacidade ativa, usando identificação e estratégia de captura existentes; comportamento observável: nenhum shiny segue para luta ou fuga deliberada
- [x] 3.2 Registrar necessidade de depósito quando shiny capturado ocupa vaga do time e executar depósito via PC existente na primeira parada segura; comportamento observável: shiny permanece armazenado e nunca participa de combate intencional
- [x] 3.3 Dirigir starter configurado pelo mode de starters com parada no shiny e evidência do save; comportamento observável: Campaign não avança com starter normal
- [x] 3.4 Dirigir primeira captura selvagem após obtenção das Poké Balls pela estratégia existente e depositar starter shiny em seguida; comportamento observável: ordem é Poké Balls, captura, cura necessária, depósito
- [x] 3.5 Preencher vagas normais até time alcançar seis usando rotina de encontro e captura existente; comportamento observável: shinies armazenados não contam como combatentes permanentes
- [x] 3.6 Encaminhar encontros únicos e lendários ao mode/controller correspondente definido no catálogo; comportamento observável: encontro com shiny possível só termina aceito após captura shiny

## 4. Seleção e manutenção da equipe

- [x] 4.1 Implementar cálculo `sum(status base) + sum(IVs)` para candidatos não shiny; confirmar por inspeção que level não aparece na pontuação nem nos desempates
- [x] 4.2 Comparar time e boxes durante acesso ao PC e montar melhores combatentes normais; comportamento observável: candidato de level menor substitui candidato de potencial inferior
- [x] 4.3 Calcular cobertura HM de cada espécie com learnset existente e selecionar menor conjunto necessário; comportamento observável: candidato único que cobre quatro HMs requeridos ocupa vaga de HM Slayer
- [x] 4.4 Substituir HM Slayer somente por cobertura estritamente melhor ou combinação com menos vagas, preservando requisitos temporários do catálogo; comportamento observável: trocas ocorrem pelo PC existente
- [x] 4.5 Reorganizar equipe mantendo shinies excluídos, vagas HM mínimas e total seis quando recursos permitirem; comportamento observável: composição resultante satisfaz regras globais e requisito temporário da missão

## 5. Treino, batalha e recuperação

- [ ] 5.1 Ler nível-alvo antes de cada missão e delegar treino dos combatentes abaixo dele ao modo existente; comportamento observável: level decide necessidade de treino, nunca seleção de combatente
- [ ] 5.2 Usar battle handler e estratégia configurada existentes em encontros e treinadores incidentais; comportamento observável: Campaign retoma mesma etapa após vitória
- [ ] 5.3 Integrar decisão de cura com saúde atual, último local de cura, enum de centros e busca de centro próximo existentes; comportamento observável: Campaign não usa loop paralelo de Pokémon Center
- [ ] 5.4 Tratar whiteout relendo retorno do save e reavaliando treino antes de repetir confronto; comportamento observável: derrota não marca etapa concluída nem causa repetição imediata sem preparo

## 6. Catálogo completo Ruby, Sapphire e Emerald

- [ ] 6.1 Cadastrar fluxo de Littleroot até Stone Badge com variantes RSE e referências a capacidades existentes; critério: cada etapa possui condição persistente de conclusão
- [ ] 6.2 Cadastrar fluxo de Rustboro, Dewford, Slateport e Dynamo Badge com variantes RSE; critério: batalhas, HMs e deslocamentos obrigatórios vêm do catálogo
- [ ] 6.3 Cadastrar fluxo de Fallarbor, Meteor Falls, Mt. Chimney, Lavaridge e Balance Badge com variantes RSE; critério: eventos exclusivos usam condições específicas por jogo
- [ ] 6.4 Cadastrar fluxo de Weather Institute, Fortree, equipes Magma/Aqua e Feather Badge com variantes RSE; critério: nenhuma decisão de missão nova fica em branch Python por versão
- [ ] 6.5 Cadastrar fluxo de Lilycove, bases Magma/Aqua, Mossdeep e Mind Badge com variantes RSE; critério: pré-requisitos de história e HM estão explícitos
- [ ] 6.6 Cadastrar fluxo de lendário principal, Sootopolis e Rain Badge com mode de reset aplicável quando encontro puder ser shiny; critério: exceções de shiny-lock ficam explícitas no catálogo
- [ ] 6.7 Cadastrar Victory Road, Elite Four e Champion com metas de treino e recuperação; critério: conclusão final deriva das flags/variáveis persistentes do save
- [ ] 6.8 Cadastrar encontros únicos ou lendários pertencentes ao fluxo Campaign com tipo e mode correspondente; critério: catálogo não cria objetivo Living Dex

## 7. Dashboard

- [ ] 7.1 Manter filtro de profiles pelo jogo e início do profile/save escolhido; comportamento observável: jogo sem profile não inicia ROM diferente
- [ ] 7.2 Manter seleção baseada em modes registrados e troca entre Manual, Campaign e modos disponíveis; comportamento observável: modo indisponível é rejeitado sem fallback silencioso
- [ ] 7.3 Expor missão, etapa, objetivo e motivo de pausa fornecidos pelo Campaign no estado existente; comportamento observável: frontend apenas apresenta estado recebido, sem inferir regra

## 8. Remoção de duplicações

- [ ] 8.1 Remover TODO e lógica parcial da captura Route 102 substituídos pela execução declarativa e capacidades existentes; confirmar ausência de segundo fluxo de captura
- [ ] 8.2 Remover branches, helpers e imports Campaign tornados sem uso pela delegação genérica; confirmar que módulos originais de batalha, cura, PC, starter e treino continuam sendo os pontos únicos de implementação
- [ ] 8.3 Revisar diff final somente contra escopo desta mudança; confirmar ausência de Living Dex, battle policy, battle handler paralelo, `pokecenter_loop` novo, framework, dependência ou infraestrutura adicional
