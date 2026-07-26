Salut Claude.

Je voudrais que tu m'aides à construire un prototype d'un appareil que l'on va appeller "M-Card".
- On met une carte RFID dans un boitier de CD ou au dos d'un Vinyle
- On pose ce CD ou ce Vinyle sur l'appareil
- L'appareil lance l'album (config RFID<>album) sur Roon
- L'appareil dispose de boutons physiques next/prev/pause/play
- L'appareil dispose d'un petit affichage qui donne le nom de l'album et le nom de la track qui joue

Ci-joint des croquis de ce à quoi l'appareil va ressembler : "idea/M-card idea.pdf"

Je dispose actuellement de:
- Imprimante 3D
- Raspberry PI 3 Model B+
- Un écran LCD (Hailege 2004 20X4 LCD, see photos "idea/LCD Screen-1.jpg" and "idea/LCD Screen-2.jpg")
- Un lecteur NFC / RFID (nfcpy donne "found ACS ACR122U PN532v1.6 at usb:001:006", qui peut être "démonté" au besoin), see photos "idea/NFC Reader-1.jpg" and "idea/NFC Reader-2.jpg"
- Carte SD
- Et bien sûr d'un stock de cartes RFID

Tu devras:
- Etablir les fichiers 3D pour l'imprimante pour le device lui-même
  - Seul port sur l'arrière de l'appareil: est un port d'alim pour l'électronique (USB-C normalement)
  - Doit supporter un CD ou un Vinyle posé verticalement de façon stable
  - Doit être simple et élégant

- Etablir le schema de cablage de l'électronique
  - L'électronique et le code associé sera testé avec un breadboard
  - L'intégration dans l'appareil devra être détaillée, autant que possible PCB custom, mais si un PCB est nécessaire, il faudra des instructions précises de comment le faire et avec quel matériel

- Etablir le code pour faire tourner l'appareil, y compris:
  - connection à l'API Roon (Mon server Roon tourne en permanence sur mon Mac)
  - lien ID RFID <-> ref album dans Roon dans un fichier de config (pour la V0.1)
  - un moyen d'ajouter des albums à cette config (ex: ajout du RFID avec une ref d'album "TODO" au fichier de config en cas de présentation d'une carte encore inconnue)
 
 *** Je suis ouvert à toutes solutions techniques (autre lecteur, autre écran, autre Raspberry, Arduino, ...) du moment que le budget reste raisonnable et que ça puisse être commandé online et livré rapidement en France. Tu es donc maître du design technique de l'électronique ***

La connection à Roon se fera soit en WIFI (prévoir alors un fichier de config pour la connection WIFI), soit en Ethernet (dans ce cas, un connecteur Ethernet PoE pourra être considéré à la place de l'alimentation USB), à toi de choisir.

L'appareil devra:
- Se connecter à Roon
- Logger tout se qui se passe
- Permettre facilement d'accéder au fichier de log (RO) et aux fichiers de configs (RW) (partage fichier ? micro server HTTP ?)
- Sinon aucune connection réseau autre (pas d'accès Internet, ..., uniquement local).

*** Tu es un ingénieur qualifié et talentueux, tu dois donc produire une solution fonctionelle rapidement et aisée à fabriquer en DIY ***





