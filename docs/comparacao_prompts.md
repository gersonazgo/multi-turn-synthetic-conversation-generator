# Comparacao entre System Prompts: nami_v0.yml, nami_v1.yml e nami.yml

## Resumo

Os tres arquivos compartilham a mesma estrutura base e o mesmo conjunto de tecnicas (T01-T22). As diferencas sao incrementais, indicando uma evolucao iterativa do prompt. Abaixo estao todas as diferencas identificadas.

---

## 1. Posicionamento das Regras de Brevidade

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Posicao no prompt | Apenas no final (CONTRATO DE SAIDA, ~linha 221) | **Duplicada**: aparece cedo (~linha 22) E no final (~linha 235) | **Duplicada**: aparece cedo (~linha 22) E no final (~linha 233) |

**Impacto**: v1 e nami.yml reforçam as regras de brevidade colocando-as no inicio do prompt, onde tem mais peso para o modelo. A duplicacao no final serve como reforco.

---

## 2. Enfase nas Regras de Brevidade

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Qualificador | "REGRAS DE BREVIDADE (duras)" | "REGRAS DE BREVIDADE (duras - **NUNCA romper essas instrucoes**)" | "REGRAS DE BREVIDADE (duras - **NUNCA romper essas instrucoes**)" |
| Demais respostas | "<= 70 palavras (exclui bullets)" | "<= 70 palavras (**inclui validacao**, exclui bullets)" | "<= 70 palavras (**inclui validacao**, exclui bullets)" |

**Impacto**: v1 e nami.yml adicionam enfase extra ("NUNCA romper") e esclarecem que a validacao conta no limite de 70 palavras, fechando uma brecha interpretativa.

---

## 3. Formato de Resposta (VALIDACAO)

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Validacao | "1-2 frases" | "1-2 frases" | "Apenas 1 frase curta" *(parece conter typo: "curta1 frases")* |
| Checagem de entendimento | "Se for checagem de entendimento, ela e a unica pergunta do turno." | "Se for checagem de entendimento, ela **DEVE** ser a unica pergunta do turno." | "Se for checagem de entendimento, ela **DEVE** ser a unica pergunta do turno." |

**Impacto**: nami.yml reduz a validacao de 1-2 frases para apenas 1, tornando as respostas mais concisas. v1 e nami.yml enfatizam com "DEVE" a exclusividade da checagem de entendimento.

---

## 4. SAFETY_BLOCK

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Texto | "ligue 188 (CVV) ou va ao pronto-socorro" | "ligue 188 (CVV) ou va ao pronto-socorro" | "ligue para **pessoas de confianca (familia, amigos ou o profissional que o acompanha)**, 188 (CVV) ou va ao pronto-socorro" |

**Impacto**: nami.yml adiciona a orientacao de ligar primeiro para pessoas de confianca e o profissional acompanhante antes do CVV, alinhando com a filosofia geral de priorizar rede de apoio pessoal.

---

## 5. Tecnica Proporcional - Verificacao de Repertorio

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Verificar repertorio do usuario | Ausente | Ausente | **Presente**: "Nesses casos, alguma tecnicas praticas e rapidas podem ajudar a trazer alivio. O/A profissional que o acompanha ja explicou/praticou alguma delas a voce?" |
| Encorajador minimo | "Te escuto. Pode seguir." | "Te escuto. Pode seguir." | "Te escuto. Pode seguir.", **nao nova frase de validacao** |

**Impacto**: nami.yml adiciona um passo para verificar se o usuario ja conhece tecnicas do profissional que o acompanha, personalizando melhor o atendimento. Tambem restringe o encorajador minimo para nao ser uma nova validacao (evitando excesso).

---

## 6. Acentuacao e Ortografia

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Estilo | Predominantemente sem acentos | Predominantemente sem acentos | **Mais acentuacao** (ex: "psiquico" -> "psiquico", "empatica" -> "empatica", "seguranca" -> "seguranca") |

**Impacto**: nami.yml tem acentuacao mais correta em diversas partes (especialmente cabecalhos de secao e blocos literais), embora nao seja 100% consistente. Melhora a legibilidade para revisores humanos.

---

## 7. Regra 1-PERGUNTA (posicionamento)

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Posicao | Apenas no final (CONTRATO DE SAIDA) | **Duplicada**: cedo (~linha 27) e no final | **Duplicada**: cedo (~linha 27) e no final |

**Impacto**: Mesmo padrao das regras de brevidade - v1 e nami.yml reforçam a regra de 1 pergunta por turno colocando-a no topo.

---

## 8. Micropassos de Seguranca (formatacao)

| Aspecto | nami_v0.yml | nami_v1.yml | nami.yml |
|---------|-------------|-------------|----------|
| Formato | Cada micropasso em linha separada | Cada micropasso em linha separada | Todos em uma unica linha separados por ";" |

**Impacto**: Diferenca apenas de formatacao, sem impacto semantico.

---

## 9. Secoes Identicas (sem diferenca)

As seguintes secoes sao identicas ou virtualmente identicas nos tres arquivos:

- Objetivo e Aviso Inicial
- Limites Gerais
- Variaveis Internas
- Fluxo Macro
- Abertura
- Escala de Sofrimento
- Triagem de Risco
- Checagem Corporal de Seguranca
- ER_BLOCK
- Reavaliacao e Plano B
- Encerramento / Privacidade / Guia de Linguagem
- Encaminhamento e Notificacao (criterios A-F)
- Primeiros Cuidados Seguros (FIRST_AID_BLOCK)
- Bloco Empatia com Brevidade
- Plano de Seguranca Engajado (CRISIS_QUEUE)
- Politica de Variedade e Rotacao de Tecnicas
- Algoritmo de escolha / Pseudocodigo de turno
- TECHNIQUE_CARDS (T01-T22)
- SELECTOR_MATRIX / INTERNAL_INTENSITY_MAP

---

## Resumo da Evolucao

```
nami_v0.yml (base)
    |
    v
nami_v1.yml (reforço estrutural)
    - Duplica regras de brevidade e 1-pergunta no topo
    - Adiciona "NUNCA romper" e "inclui validacao"
    - Enfatiza "DEVE" na checagem de entendimento
    |
    v
nami.yml (refinamento clinico)
    - Herda tudo de v1
    - Reduz validacao de 1-2 frases para 1 frase
    - Expande SAFETY_BLOCK com rede de apoio pessoal
    - Adiciona verificacao de repertorio tecnico do usuario
    - Restringe encorajador minimo
    - Melhora acentuacao geral
```

### Direcao geral da evolucao

1. **Brevidade**: cada versao reforça mais os limites de palavras e reduz redundancias na resposta
2. **Rede de apoio**: evolui de CVV como primeira opcao para priorizar pessoas de confianca e profissional acompanhante
3. **Personalizacao**: nami.yml tenta adaptar as tecnicas ao repertorio que o usuario ja tem do seu profissional
4. **Robustez do prompt**: regras criticas sao duplicadas no inicio para garantir adesao do modelo
