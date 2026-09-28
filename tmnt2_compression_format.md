# Format de compression graphique — TMNT II: Back from the Sewers (Game Boy)

Reverse-ingénierie basée sur la routine de décompression Z80 trouvée à `label17B2` et suivantes
dans la ROM `Teenage Mutant Ninja Turtles II - Back from the Sewers (USA).gb`.

## Vue d'ensemble du flux compressé

Le flux est une suite d'**opcodes**, chacun commençant par un octet de contrôle, jusqu'à un octet
`$00` qui termine le flux. Pas d'en-tête de taille : seul le terminateur marque la fin.

| Octet de contrôle `c` | Opération |
|---|---|
| `$00` | Fin du flux |
| `c` avec bit7=0 (`$01`-`$7F`) | **RLE** : répète 1 octet lu du flux, `c` fois |
| `c` avec bit7=1, `c & $7F` ≠ 0 (`$81`-`$FF`) | **Littéral** : copie `c & $7F` octets bruts du flux |
| `c == $80` | **Commande étendue** (voir ci-dessous) |

### Commande étendue (`$80` suivi d'un octet `d2`)

| `d2` | Opération |
|---|---|
| bit7=0 (`d2` = `$01`-`$7F`) | **INC** : lit 1 octet de départ, écrit `d2` octets consécutifs croissants (`x, x+1, x+2, ...`) |
| bit7=1, type = `d2 & $7F` | **PAIR** : lit un octet `n` (nombre de paires), puis `n` octets source ; pour chacun écrit une paire de 2 octets en sortie selon le type |

### Types PAIR (type = `d2 & $7F`)

| Type | Paire écrite (à partir de l'octet source `x` lu) |
|---|---|
| 1 | `(x, $00)` |
| 2 | `($00, x)` |
| 3 | `(x, x)` |
| 4 | `($FF, x)` |
| 5 | `(x, $FF)` |
| 6 (autre) | `(~x, x)` (complément à 1 de x, puis x) |

## Seuils observés dans les données originales du jeu

En analysant les blocs réels de la ROM, l'outil de compression original (Konami, ~1991) n'utilise
jamais un opcode spécial en dessous de ces longueurs minimales — probablement des seuils fixes
codés en dur, pas un calcul d'optimalité complet :

- **RLE** : utilisé seulement si la répétition fait **≥ 3** octets
- **INC** : utilisé seulement si la séquence croissante fait **≥ 3** octets
- **PAIR** (tous types) : utilisé seulement si **≥ 4** paires

**Important** : nous avons vérifié qu'un encodeur *mathématiquement optimal* (programmation
dynamique complète) produit un résultat **plus petit** que l'original sur les 3 blocs testés.
L'outil original n'était donc pas optimal — il suit une heuristique simple, pas toujours cohérente
sur les cas d'égalité. Reproduire ses choix octet pour octet nécessiterait son code source
d'origine (l'outil PC des développeurs), qui n'est pas présent dans la ROM.

## Adresses connues dans cette ROM (offsets fichier directs, pas d'adresse bank/GB)

| Bloc | Début | Fin (exclusif, après terminateur) | Taille compressée | Taille décompressée |
|---|---|---|---|---|
| 1 | `$342DA` | `$3490A` | 1584 | 2016 (126 tuiles) |
| 2 | `$3497D` | `$35134` | 1975 | 2032 (127 tuiles) |
| 3 | `$35134` | `$356C6` | 1426 | 1488 (93 tuiles) |

## Code Python

Voir les fichiers joints `decompress.py` (décompresseur, fidèle à l'algorithme Z80 d'origine) et
`compress.py` (compresseur optimal par programmation dynamique — `optimal_compress()`).

Utilisation :
```python
from decompress import decompress
from compress import optimal_compress

rom = open("rom.gb", "rb").read()
data, end_offset = decompress(rom, 0x3497D)   # décompresse à partir d'un offset
recompressed = optimal_compress(data)          # recompresse (taille optimale, pas garantie identique à l'originale)
```

## Limitation connue pour la réinsertion dans la ROM

Le recompresseur ne reproduit pas forcément la même taille que le bloc d'origine. Avant de
réinjecter dans une ROM, toujours vérifier que `len(recompressed) <= taille_originale_du_bloc` :
si c'est le cas, on peut écrire par-dessus en remplissant le surplus avec des octets de bourrage
(jamais lus, car la décompression s'arrête au terminateur `$00`) ; sinon, la réinsertion directe
décalerait/écraserait les données suivantes dans la ROM.
