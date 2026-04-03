# Comparacao Detalhada por Diff: nami_v0.yml -> nami_v1.yml -> nami.yml

---

## Diff 1: nami_v0.yml -> nami_v1.yml

O diff entre v0 e v1 e pequeno e focado em **reforco estrutural** das regras de brevidade.

### Mudanca 1.1 — Duplicacao das regras de brevidade no topo

**Adicionado apos LIMITES GERAIS (linha ~22):**

```diff
+  REGRAS DE BREVIDADE (duras - NUNCA romper essas instruções)
+  Primeira resposta do atendimento: <= 90 palavras (exclui bullets).
+  Demais respostas: <= 70 palavras (inclui validação, exclui bullets).
+  Respostas de seguranca (ER_BLOCK/SAFETY_BLOCK): <= 120 palavras.
+  Maximo 2 paragrafos curtos antes dos bullets. Nao repetir avisos/historico.
+  REGRA 1-PERGUNTA
+  Exatamente uma pergunta por turno. Se precisar de duas, escolher a mais critica e deixar a outra para o proximo turno.
```

### Mudanca 1.2 — Enfase "NUNCA romper" e esclarecimento de contagem

**No CONTRATO DE SAIDA (final do prompt):**

```diff
-  REGRAS DE BREVIDADE (duras)
+  REGRAS DE BREVIDADE (duras - NUNCA romper essas instruções)

-  Demais respostas: <= 70 palavras (exclui bullets).
+  Demais respostas: <= 70 palavras (inclui validação, exclui bullets).
```

### Mudanca 1.3 — Enfase "DEVE" na checagem de entendimento

```diff
-  Observacao: validar sempre; tecnica apenas quando indicada; pergunta sempre unica.
-  Se for checagem de entendimento, ela e a unica pergunta do turno.
+  Observacao: validar sempre; técnica apenas quando indicada; pergunta sempre unica.
+  Se for checagem de entendimento, ela DEVE ser a única pergunta do turno.
```

### Mudanca 1.4 — Acentuacao pontual

```diff
-  FORMATO DE RESPOSTA (obrigatorio, toda mensagem)
+  FORMATO DE RESPOSTA (obrigatório, toda mensagem)

-  TECNICA (se aplicavel):
+  TECNICA (se aplicável):
```

### Resumo v0 -> v1

| Tipo de mudanca | Quantidade | Impacto |
|-----------------|-----------|---------|
| Duplicacao de regras no topo | 1 bloco (8 linhas) | Alto — posicionamento estrategico |
| Reforco enfatico ("NUNCA", "DEVE") | 2 | Alto — compliance do modelo |
| Esclarecimento de contagem (validacao inclusa) | 1 | Alto — fecha brecha interpretativa |
| Acentuacao | 2 | Baixo — cosmetico |

---

## Diff 2: nami_v1.yml -> nami.yml

O diff entre v1 e nami.yml e significativamente maior, com mudancas semanticas e clinicas alem de correcoes ortograficas massivas.

### Mudanca 2.1 — Acentuacao generalizada

Dezenas de linhas foram atualizadas para incluir acentos corretos. Exemplos representativos:

```diff
-  Responder a pessoas em sofrimento psiquico de forma empatica, segura...
+  Responder a pessoas em sofrimento psíquico de forma empática, segura...

-  Nao mostrar processos internos, placeholders ou variaveis.
+  Não mostrar processos internos, placeholders ou variáveis.

-  Nunca diagnosticar, prescrever, prometer cura ou ensinar metodos letais.
+  Nunca diagnosticar, prescrever, prometer cura ou ensinar métodos letais.
```

### Mudanca 2.2 — SAFETY_BLOCK expandido com rede de apoio

```diff
-  "Se sentir que pode se machucar, ligue 188 (CVV) ou va ao pronto-socorro.
-  Vou avisar seu contato de emergencia agora.
-  Vou ficar com voce ate estar seguro e a ajuda ser confirmada."
+  "Se sentir que pode se machucar, ligue para pessoas de confiança
+  (família, amigos ou o profissional que o acompanha), 188 (CVV) ou
+  vá ao pronto-socorro. Vou avisar seu contato de emergência agora.
+  Vou ficar com você até estar seguro e a ajuda ser confirmada."
```

### Mudanca 2.3 — Verificacao de repertorio tecnico do usuario

```diff
   Checar entendimento: "Estou entendendo X e Y; e isso mesmo?"
-  So entao explicar a tecnica, pedir consentimento e direcionar o uso
+  Verificar se a pessoa conhece ou tem preferência por alguma técnica:
+  "Nesses casos, alguma técnicas práticas e rápidas podem ajudar a trazer
+  alívio. O/A profissional que o acompanha já explicou/praticou alguma
+  delas a você?"
+  Só então explicar a técnica, pedir consentimento e direcionar o uso
```

### Mudanca 2.4 — Restricao no encorajador minimo

```diff
-  Estimular fala com encorajador minimo (ex.: "Te escuto. Pode seguir.")
+  Estimular fala com encorajador minimo (ex.: "Te escuto. Pode seguir."),
+  não nova frase de validação
```

### Mudanca 2.5 — Reducao da validacao de 1-2 para 1 frase

```diff
-  VALIDACAO: 1–2 frases.
+  VALIDAÇÃO: Apenas 1 frase curta1 frases.
```

### Mudanca 2.6 — "Nao validar o invalido" reformatado

```diff
-  Nao validar o invalido (linguagem pronta)
-  "Entendo que voce sentiu alivio; isso mostra o quanto estava intenso..."
-  "Eu escuto o 'so quero parar de pensar'; suprimir pensamento..."
+  Não validar o invalido (linguagem pronta) - exemplos de frase
+  "Entendo que você sentiu alivio; ..." ; "Eu escuto o 'só quero..."
```

### Mudanca 2.7 — Micropassos de seguranca compactados

```diff
-  Se for seguro, mova-se para perto de uma porta...
-  Deixe a porta destrancada se isso for seguro para voce.
-  Se houver alguem de confianca, chame essa pessoa agora.
-  Se piorar fisicamente, ligue 192 imediatamente.
+  "Se for seguro, mova-se..."; "Deixe a porta destrancada...";
+  "Se houver alguem..."; "Se piorar fisicamente, ligue 192..."
```

### Mudanca 2.8 — Typo introduzido na abertura

```diff
-  Depois: validacao breve (nivel 3). Não prefixar validacao com "validacao".
+  Depois: vValidacao breve (nivel 3). Não prefixar validacao com "validacao".
```

### Mudanca 2.9 — Quebra de linha corrigida

```diff
-  Permitir apenas condutas minimas e seguras em casos LEVES. Em casos GRAVES, acionar emergencia (192) e 
-  PLANO DE SEGURANCA ENGAJADO.
+  Permitir apenas condutas mínimas e seguras em casos LEVES. Em casos GRAVES, acionar emergencia (192) e PLANO DE SEGURANCA ENGAJADO.
```

### Mudanca 2.10 — T22 com acentuacao

```diff
-  T22 | Meio sorriso e maos dispostas | Reforcar atitude de aceitacao |
+  T22 | Meio sorriso e mãos dispostas | Reforçar atitude de aceitação |
```

### Resumo v1 -> nami.yml

| Tipo de mudanca | Quantidade | Impacto |
|-----------------|-----------|---------|
| Acentuacao sistematica | ~60 linhas | Medio — coerencia ortografica |
| SAFETY_BLOCK expandido (rede de apoio) | 1 | **Alto** — mudanca clinica |
| Verificacao de repertorio tecnico | 1 bloco novo | **Alto** — personalizacao |
| Restricao encorajador (nao = validacao) | 1 | Medio — brevidade |
| Validacao reduzida (1-2 -> 1 frase) | 1 | Alto — brevidade |
| Reformatacao/compactacao | 3 | Baixo — cosmetico |
| Typos introduzidos | 2 ("vValidacao", "curta1") | Baixo — bugs |

---

## Evolucao do Prompt

### Diagrama de evolucao

```
╔══════════════════════════════════════════════════════════════════════════╗
║  nami_v0.yml — BASE FUNCIONAL                                         ║
║                                                                        ║
║  O que estabelece:                                                     ║
║  • Fluxo macro de 7 etapas:                                           ║
║    Abertura -> Escala 1-10 -> Triagem de risco -> Checagem corporal    ║
║    -> Tecnica proporcional -> Reavaliacao -> Encerramento              ║
║  • 22 tecnicas DBT em 3 familias:                                     ║
║    F1 Mindfulness (T01-T08), F2 Tolerancia (T09-T18),                 ║
║    F3 Aceitacao (T19-T22)                                             ║
║  • Protocolos de crise: SAFETY_BLOCK, ER_BLOCK, FIRST_AID_BLOCK,      ║
║    Plano de Seguranca Engajado com CRISIS_QUEUE                       ║
║  • Sistema de estado interno: 20+ variaveis ([NIVEL], [CRISIS_MODE],  ║
║    [RISCO_POTENCIAL], [used_TIDs], etc.)                              ║
║  • Regras de formato: brevidade (70-90 palavras), 1 pergunta/turno,   ║
║    politica anti-repeticao com cooldown de tecnicas                    ║
║  • Criterios de encaminhamento (A-F) para acionar emergencia          ║
║                                                                        ║
║  Posicionamento das regras de brevidade:                               ║
║    Apenas no FINAL do prompt (secao CONTRATO DE SAIDA, ~linha 221)    ║
║                                                                        ║
║  Regras de brevidade:                                                  ║
║    "REGRAS DE BREVIDADE (duras)"                                       ║
║    "Demais respostas: <= 70 palavras (exclui bullets)"                 ║
║    → nao especifica se validacao conta ou nao nos 70 palavras          ║
║                                                                        ║
║  Formato de validacao:                                                 ║
║    "VALIDACAO: 1-2 frases"                                             ║
║    "Se for checagem de entendimento, ela e a unica pergunta do turno"  ║
║                                                                        ║
║  SAFETY_BLOCK:                                                         ║
║    "ligue 188 (CVV) ou va ao pronto-socorro"                           ║
║    → CVV como primeira e unica opcao de contato                        ║
║                                                                        ║
║  Tecnica proporcional — fluxo:                                         ║
║    Encorajador -> Identificar necessidade -> Checar entendimento       ║
║    -> Explicar tecnica -> Pedir consentimento                          ║
╚══════════════════════════════════════════════════════════════════════════╝
         │
         ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  nami_v1.yml — REFORCO ESTRUTURAL (engenharia de prompt)               ║
║                                                                        ║
║  Nenhuma mudanca clinica. Foco: compliance do modelo com brevidade.    ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 1: POSICIONAMENTO ESTRATEGICO                          │    ║
║  │                                                                 │    ║
║  │ Regras de brevidade + regra 1-pergunta DUPLICADAS no topo      │    ║
║  │ do prompt (~linha 22), logo apos LIMITES GERAIS.               │    ║
║  │ Mantidas tambem no final (CONTRATO DE SAIDA).                  │    ║
║  │                                                                 │    ║
║  │ O que muda na pratica: o modelo encontra os limites de         │    ║
║  │ palavras e a regra de 1 pergunta logo no inicio, antes de      │    ║
║  │ processar o restante do prompt. A duplicacao no final           │    ║
║  │ reforça essas mesmas regras.                                    │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 2: LINGUAGEM IMPERATIVA                                │    ║
║  │                                                                 │    ║
║  │ Antes: "REGRAS DE BREVIDADE (duras)"                           │    ║
║  │ Depois: "REGRAS DE BREVIDADE (duras - NUNCA romper essas       │    ║
║  │          instrucoes)"                                           │    ║
║  │                                                                 │    ║
║  │ Antes: "ela e a unica pergunta do turno"                       │    ║
║  │ Depois: "ela DEVE ser a unica pergunta do turno"               │    ║
║  │                                                                 │    ║
║  │ O que muda na pratica: troca de tom descritivo ("e") para      │    ║
║  │ imperativo ("DEVE", "NUNCA"), sinalizando que essas regras     │    ║
║  │ nao sao flexiveis.                                              │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 3: BRECHA DE CONTAGEM FECHADA                          │    ║
║  │                                                                 │    ║
║  │ Antes: "Demais respostas: <= 70 palavras (exclui bullets)"     │    ║
║  │ Depois: "Demais respostas: <= 70 palavras (inclui validacao,   │    ║
║  │          exclui bullets)"                                       │    ║
║  │                                                                 │    ║
║  │ O que muda na pratica: a validacao agora e contabilizada       │    ║
║  │ dentro do limite de 70 palavras. Antes, a ausencia dessa       │    ║
║  │ especificacao permitia que validacao + conteudo + pergunta     │    ║
║  │ ultrapassassem o limite.                                        │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  O que NAO mudou:                                                      ║
║  • Fluxo macro (7 etapas)                                             ║
║  • Tecnicas e familias (T01-T22, F1-F3)                               ║
║  • Protocolos de crise (SAFETY/ER/FIRST_AID BLOCKS)                   ║
║  • Criterios de encaminhamento (A-F)                                   ║
║  • CRISIS_QUEUE e Plano de Seguranca Engajado                         ║
║  • Variaveis internas                                                  ║
║  • SELECTOR_MATRIX e INTENSITY_MAP                                     ║
╚══════════════════════════════════════════════════════════════════════════╝
         │
         ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  nami.yml — REFINAMENTO CLINICO + ORTOGRAFICO                          ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 1: SAFETY_BLOCK — REDE DE APOIO PESSOAL                │    ║
║  │                                                                 │    ║
║  │ Antes: "ligue 188 (CVV) ou va ao pronto-socorro"               │    ║
║  │ Depois: "ligue para pessoas de confianca (familia, amigos      │    ║
║  │          ou o profissional que o acompanha), 188 (CVV)          │    ║
║  │          ou va ao pronto-socorro"                               │    ║
║  │                                                                 │    ║
║  │ O que muda na pratica: em risco positivo, o modelo agora       │    ║
║  │ orienta o usuario a procurar primeiro quem ja o conhece         │    ║
║  │ (familia, amigos, psicologo/psiquiatra), e so depois o CVV.    │    ║
║  │ Antes, a unica orientacao de contato era o 188. Agora a        │    ║
║  │ rede pessoal aparece antes do CVV, alinhando o SAFETY_BLOCK   │    ║
║  │ com a regra ja existente de priorizar "pessoa de confianca"    │    ║
║  │ — que antes so valia para leve/moderado e agora se estende     │    ║
║  │ tambem aos casos graves.                                        │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 2: VERIFICACAO DE REPERTORIO TECNICO                   │    ║
║  │                                                                 │    ║
║  │ Novo passo adicionado ao fluxo de TECNICA PROPORCIONAL:        │    ║
║  │                                                                 │    ║
║  │ v0/v1: Checar entendimento -> Explicar tecnica                 │    ║
║  │ nami:  Checar entendimento -> PERGUNTAR SE O PROFISSIONAL      │    ║
║  │        JA ENSINOU ALGUMA TECNICA -> Explicar tecnica            │    ║
║  │                                                                 │    ║
║  │ Frase inserida: "Nesses casos, alguma tecnicas praticas e      │    ║
║  │ rapidas podem ajudar a trazer alivio. O/A profissional que     │    ║
║  │ o acompanha ja explicou/praticou alguma delas a voce?"         │    ║
║  │                                                                 │    ║
║  │ O que muda na pratica: se o usuario responde "sim, meu         │    ║
║  │ psicologo me ensinou respiracao", o modelo pode reforcar       │    ║
║  │ essa tecnica conhecida em vez de sugerir algo novo. Se          │    ║
║  │ responde "nao", segue o fluxo normal. Adiciona 1 turno        │    ║
║  │ extra ao fluxo de tecnica proporcional.                         │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 3: VALIDACAO MAIS ENXUTA                               │    ║
║  │                                                                 │    ║
║  │ Duas restricoes combinadas:                                     │    ║
║  │                                                                 │    ║
║  │ a) Formato de validacao reduzido:                               │    ║
║  │    Antes: "VALIDACAO: 1-2 frases"                               │    ║
║  │    Depois: "VALIDACAO: Apenas 1 frase curta"                    │    ║
║  │                                                                 │    ║
║  │ b) Encorajador minimo restringido:                              │    ║
║  │    Antes: "Estimular fala com encorajador minimo"               │    ║
║  │    Depois: "Estimular fala com encorajador minimo,              │    ║
║  │             nao nova frase de validacao"                         │    ║
║  │                                                                 │    ║
║  │ Efeito combinado: antes o modelo podia gerar validacao          │    ║
║  │ (2 frases) + encorajador (que tambem era validacao) =           │    ║
║  │ 3 frases empaticas por turno. Agora: 1 frase curta de          │    ║
║  │ validacao + encorajador que NAO e validacao = resposta          │    ║
║  │ mais direta e menos repetitiva emocionalmente.                  │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ Mudanca 4: COERENCIA ORTOGRAFICA                               │    ║
║  │                                                                 │    ║
║  │ ~60 linhas corrigidas com acentuacao adequada.                  │    ║
║  │ Exemplos: "empatica" -> "empatica", "tecnica" -> "tecnica",    │    ║
║  │ "seguranca" -> "seguranca", "psiquico" -> "psiquico"           │    ║
║  │                                                                 │    ║
║  │ O que muda na pratica: o prompt passa a ser coerente com       │    ║
║  │ sua propria regra "Sempre usar portugues brasileiro com        │    ║
║  │ ortografia e acentuacao correta". A acentuacao nao e           │    ║
║  │ 100% uniforme — ainda ha trechos sem acentos.                  │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  O que MUDOU (acumulado v0 -> v1 -> nami.yml):                         ║
║  • Regras de brevidade duplicadas no topo do prompt (v1)               ║
║  • Linguagem imperativa: "NUNCA romper", "DEVE" (v1)                   ║
║  • Validacao conta dentro do limite de 70 palavras (v1)                ║
║  • SAFETY_BLOCK: rede pessoal antes do CVV (nami.yml)                  ║
║  • Novo passo: verificar repertorio tecnico do profissional (nami.yml) ║
║  • Validacao reduzida de 1-2 frases para 1 frase curta (nami.yml)     ║
║  • Encorajador minimo nao pode ser frase de validacao (nami.yml)       ║
║  • Acentuacao corrigida em ~60 linhas (nami.yml)                       ║
║                                                                        ║
║  O que NAO mudou (preservado desde v0):                                ║
║  • Fluxo macro de 7 etapas                                            ║
║  • 22 tecnicas e 3 familias (T01-T22, F1-F3)                          ║
║  • SELECTOR_MATRIX e INTENSITY_MAP                                     ║
║  • Protocolos de crise (ER_BLOCK, FIRST_AID_BLOCK, CRISIS_QUEUE)      ║
║  • Criterios de encaminhamento (A-F)                                   ║
║  • Sistema de variaveis internas (20+)                                 ║
║  • Politica anti-repeticao e cooldown                                  ║
║  • Pseudocodigo de turno                                               ║
║  • Limites de palavras (90 primeira / 70 demais / 120 seguranca)      ║
║                                                                        ║
║  ⚠️  Regressoes (typos introduzidos por edicao manual):                ║
║  • "vValidacao" (linha 60) — "v" duplicado                             ║
║  • "curta1 frases" (linha 228) — "1" colado em "curta"                ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Resumo: eixos de evolucao

| Eixo | v0 | v1 | nami.yml |
|------|----|----|----------|
| **Brevidade** | Regras no final, tom descritivo, validacao fora da contagem | Regras duplicadas no topo, "NUNCA romper", validacao dentro da contagem | Validacao reduzida a 1 frase, encorajador != validacao |
| **Seguranca (crise)** | CVV como unica orientacao de contato no SAFETY_BLOCK | Sem mudanca | Rede pessoal (familia, amigos, profissional) antes do CVV |
| **Personalizacao** | Mesma abordagem para todos os usuarios | Sem mudanca | Pergunta se o profissional ja ensinou tecnicas ao usuario |
| **Ortografia** | Sem acentos na maior parte do prompt | Acentos pontuais (3-4 palavras) | Correcao sistematica (~60 linhas) |
| **Conteudo clinico** | Completo (22 tecnicas, 3 familias, 6 criterios de encaminhamento, CRISIS_QUEUE) | Identico ao v0 | Identico ao v0, com adição do passo de repertorio |

### Narrativa para apresentacao

1. **v0 entregou a arquitetura completa** — todo o conteudo (22 tecnicas, protocolos de crise, criterios de encaminhamento, fluxo de 7 etapas) ja estava presente. As regras de brevidade existiam, mas ficavam apenas no final do prompt.

2. **v1 focou em engenharia de prompt** sem tocar no conteudo. Foram 3 mudancas: (a) duplicar regras de brevidade e 1-pergunta no topo, (b) trocar linguagem descritiva por imperativa ("NUNCA", "DEVE"), (c) especificar que a validacao conta dentro do limite de 70 palavras.

3. **nami.yml fez ajustes de conteudo e ortografia**: (a) SAFETY_BLOCK passou a listar rede pessoal antes do CVV, (b) novo passo pergunta se o profissional ja ensinou tecnicas, (c) validacao reduzida de 1-2 para 1 frase, (d) encorajador nao pode ser validacao, (e) correcao de acentuacao em ~60 linhas.
