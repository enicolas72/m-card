# Assemblage — M-Card

Prérequis : les 4 pièces imprimées (cf. `hardware/enclosure/README.md`),
la visserie de la BOM, et l'électronique **déjà validée sur breadboard**
(cf. `docs/WIRING.md`).

## 1. Ouvrir l'ACR122U

1. Décoller les 4 patins sous le lecteur, retirer les 4 vis.
2. Sortir la carte nue (antenne = la boucle de piste autour du bord).
3. Mesurer la carte et comparer aux paramètres `reader_*` de `mcard.scad`
   (défaut 95 × 65 × 10 mm) — réimprimer le dosseret si besoin.

## 2. Façade (corps principal)

1. **LCD** : présenter le module par l'intérieur, la dalle dans la fenêtre,
   visser 4 × M3×8 dans les plots. Le potentiomètre de contraste reste
   accessible boîtier ouvert.
2. **Boutons** : enficher les 3 boutons 12 mm dans les perçages
   (⏮ ⏯ ⏭ de gauche à droite), serrer les écrous.
3. Câbler LCD et boutons vers le GPIO selon `WIRING.md` (câbles Dupont).

## 3. Dosseret + lecteur

1. Passer le câble USB d'origine du lecteur par l'ouverture basse du
   dosseret et le trou oblong de la face supérieure du corps (la prise
   USB-A passe par le trou oblong de 14 mm ; l'excédent de câble
   s'enroule dans le socle).
2. Coller la carte du lecteur dans son logement (adhésif double face),
   antenne vers l'avant (côté fente).
3. Visser la plaque arrière (4 × M3×8).
4. Poser le dosseret sur le corps : les 2 pions s'alignent, puis 2 × M3×12
   par l'intérieur du boîtier, à travers la face supérieure.

## 4. Arrière et fond

1. Visser l'embase USB-C panneau à l'arrière (2 × M2), brancher le
   pigtail micro-USB sur le port d'alimentation du Pi.
2. Visser le Raspberry Pi sur les plots du fond (4 × M2,5×6), ports USB
   orientés vers l'arrière.
3. Brancher : câble du lecteur → USB du Pi, Dupont LCD/boutons → GPIO.
4. Fermer le fond (4 × M3×10 fraisées).

## 5. Test final

1. Brancher le chargeur USB-C : le LCD doit afficher « Posez un album »
   en ~30 s.
2. Poser un boîtier CD avec carte RFID dans la fente : lecture Roon.
3. Vérifier les 4 boutons, puis `http://mcard.local:8088/`.

## Conseils

- Le boîtier CD se pose **carte RFID vers l'arrière** (côté dosseret).
  Pour un vinyle, glisser la carte dans la pochette, coin bas, côté
  dosseret. Marquer le coin d'une pastille discrète pour retrouver le sens.
- Si la lecture est capricieuse à travers la pochette : rapprocher la
  carte du coin bas-arrière (portée ~4 cm depuis l'antenne).
- Gaine spirale ou colliers pour les câbles internes : le fond se referme
  sans pincer.
