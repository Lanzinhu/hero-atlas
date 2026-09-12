---
tipo: decisao
id: ADR-008
estado: aceita
data: 2026-09-12
tags: [propulsao, epistemologia, arquitetura]
---

# ADR-008 — Ramos de propulsão coexistem, e a seleção é estruturalmente impossível hoje

## Contexto

Depois do [[Experimento 1 - Geometria de autoridade]], com **zero** dinâmica
implementada, o projeto produziu a frase "recomendação: combustão". A revisão externa
recusou, e estava certa:

> Os resultados atuais não selecionam um motor nem aprovam uma tecnologia. Eles
> mostram que, sob as hipóteses de massa, energia e geometria avaliadas, certas metas
> de autonomia elétrica exigem área propulsiva potencialmente incompatível com a
> arquitetura vestível de braços vetorizados.

A diferença entre as duas frases não é de tom, é de conteúdo. "Combustão aprovada"
exigiria que a família de atraso e rampa sobrevivesse aos marcos 3 a 5.

Convenção não segurou a distinção: falhou na primeira oportunidade. O mesmo já tinha
acontecido com [[ADR-007 - Deck de propulsao instalada]], e a resposta lá foi tornar a
marca estrutural. A resposta aqui é a mesma.

## Decisão

Os ramos tecnológicos vivem em `src/hero_atlas/propulsion_family.py`, e o mecanismo
tem três partes que se sustentam mutuamente:

1. **`FamilyStatus` não tem valor de aprovação.** Os três valores são
   `UNEVALUATED`, `CANDIDATE` e `INCOMPATIBLE_UNDER_HYPOTHESIS`. Não existe como
   escrever "aprovado".
2. **`CANDIDATE` exige pelo menos uma incógnita bloqueante declarada.** Candidata sem
   nada bloqueando é aprovação com outro nome, e o construtor recusa.
3. **`selection_verdict` só devolveria `SATISFIED` diante de uma candidata sem
   bloqueio**, que o item 2 torna inconstruível. Hoje devolve `INDETERMINATE` **por
   construção**, não por acaso do estado atual.

Uma incógnita só sai da lista quando um marco produzir o dado. Aí o veredito muda
sozinho, sem ninguém reescrever conclusão.

## Eliminação é sempre condicional

`INCOMPATIBLE_UNDER_HYPOTHESIS` carrega obrigatoriamente o campo `eliminated_by`, com
a hipótese que elimina. Mudou a hipótese, o ramo volta para a mesa. Eliminação sem
hipótese registrada não pode ser revisitada e vira dogma, então o construtor recusa.

## Os quatro ramos

| Ramo | Estado | Observação |
|---|---|---|
| `turbina_compacta` | candidato | 4 incógnitas, sendo a central o atraso de degrau pequeno |
| `hibrido_turbina_com_buffer` | candidato | 7 incógnitas; ataca a incógnita central diretamente |
| `hibrido_serie` | candidato | 4 incógnitas; decide na potência específica do gerador |
| `eletrico_distribuido` | eliminado sob hipótese | teto de 2,98 min por saturação de massa |

## Duas eliminações que foram retiradas, e por quê

⚠ Esta seção existe porque os dois erros são do mesmo tipo e não podem se repetir.

**Elétrico distribuído.** A justificativa original era "a área de disco exigida implica
diâmetro de rotor incompatível com o braço humano".
O [[Experimento 2 - Energia por missao]] mostrou que isso é **falso** na escala em
questão: com sete rotores de 22 cm o
trim fecha e o traje voa. O limite real é outro e mais duro: o ótimo de bateria pede
190 kg, a geometria só equilibra até 208,1 kg brutos, e exigir aceleração de subida
corta o teto para 103 kg de bateria. Preso a isso, o melhor caso elétrico é 2,98 min,
que a combustão alcança com 12,0 kg de combustível. O ramo está eliminado por
**saturação de massa**, não por geometria de rotor.

**Híbrido série.** A justificativa original era "resolve energia, não área". A frase
confundia **energia** com **potência**. É verdade que a área limita a potência de
pairado e que o híbrido série não a melhora. Mas a autonomia do elétrico puro não é
limitada por potência: é limitada por massa de bateria, que satura contra o teto de
trim. Trocar bateria por gerador mais combustível ataca exatamente essa saturação. A
eliminação foi **retirada**, e o ramo agora depende de um número mensurável: quilowatt
por quilograma do conjunto gerador mais eletrônica, contra uma exigência de 103 a
235 kW de barramento conforme a massa bruta.

## Massa seca é específica da família

⚠ Toda comparação feita até aqui fixa a **mesma massa seca** para todas as famílias.
Isso torna a comparação controlada e é também o seu limite: compara **armazenamento de
energia sob geometria fixa**, não arquiteturas completas.

Motores, inversores e gerenciamento de bateria de um lado; unidade de controle,
tanques e linhas do outro. Nenhum entrou no livro de massa. Está registrado como
incógnita bloqueante nos quatro ramos, e é o que impede chamar o Experimento 2 de
comparação arquitetural.

## Consequência

Nenhum relatório do projeto pode dizer "combustão aprovada" ou "elétrico descartado"
sem qualificação. A forma correta está em `selection_verdict`, e o
[[Experimento 2 - Energia por missao]] a imprime junto de todo resultado.

Ver [[R-04 - Resultado humano e condicional]] para a regra irmã do lado humano.
