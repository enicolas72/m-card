# Assemblage — M-Card (boîtier V0.3)

Prérequis : les 5 pièces imprimées (cf. `hardware/enclosure/README.md`),
14 inserts filetés M3, la visserie, et l'électronique **déjà validée sur
breadboard** (cf. `docs/WIRING.md`).

## 1. Inserts filetés

Chaque emplacement a une poche chanfreinée : poser l'insert dedans (il se
centre seul), presser au fer à souder (~230 °C pour du PLA), laisser refroidir.

- 4 dans le cadre avant du corps (depuis l'avant),
- 4 dans les bosses du fond (depuis le dessous),
- 2 sous le dosseret, 4 à l'arrière du dosseret.

## 2. Façade (à plat, sur l'établi)

1. **LCD** : poser le module sur les 4 plots, dalle dans la fenêtre, visser
   4 × M3×8 CHC dans les avant-trous Ø2,8 (la vis se taraude dans le PLA) —
   accès direct, la façade est à plat.
2. **Boutons** : enficher les 3 boutons 12 mm (⏮ en bas, ⏯ au milieu,
   ⏭ en haut — icônes gravées en regard), serrer les écrous.
3. Câbler LCD et boutons (câbles Dupont, cf. WIRING.md), puis **visser la
   façade** sur la console inclinée du socle : 4 × M3×8 CHC (têtes noyées
   dans les lamages).

## 3. Dosseret + lecteur

1. Passer la prise USB-A du câble du lecteur par le passage oblong du
   dosseret (côté droit) puis celui de la face supérieure du socle
   (l'excédent de câble s'enroule dans le socle).
2. Coller la carte du lecteur contre la paroi avant de la cavité (adhésif
   double face), **en paysage entre les deux butées : antenne — la grande
   zone plane — à gauche, câble sortant à droite**, composants vers
   l'arrière. Le reste de la cavité reste libre pour le câble.
3. Visser la plaque arrière affleurante (4 × M3×8 CHC).
4. Poser le dosseret sur le corps : les 2 pions s'alignent, puis 2 × M3×8 CHC
   par l'intérieur du boîtier, à travers la face supérieure.

## 4. Arrière et fond

1. Visser l'embase USB-C panneau à l'arrière (2 × M2), brancher le
   pigtail micro-USB sur le port d'alimentation du Pi.
2. Visser le Raspberry Pi sur les plots du fond (4 × M2,5×6), ports USB
   vers l'arrière.
3. Brancher : câble du lecteur → USB du Pi, Dupont LCD/boutons → GPIO.
4. Fermer le fond (4 × M3×8 CHC, têtes noyées).

## 5. Test final

1. Brancher le chargeur USB-C : « Posez un album » s'affiche en ~30 s.
2. Poser un boîtier CD avec carte RFID dans la fente : lecture Roon.
3. Poser un vinyle : la fente traversante le laisse reposer au fond de la
   rainure, adossé au dosseret.
4. Vérifier les 3 boutons, puis `http://mcard.local:8088/`.

## Conseils

- Le boîtier CD se pose **carte RFID vers l'arrière** (côté dosseret).
  Pour un vinyle, glisser la carte dans la pochette, coin bas, côté
  dosseret ; marquer le coin d'une pastille discrète.
- Si la lecture est capricieuse à travers la pochette : rapprocher la
  carte du coin bas-arrière (portée ~4 cm depuis l'antenne).
- Gaine spirale ou colliers pour les câbles internes : le fond se referme
  sans pincer.
