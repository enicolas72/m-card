// ============================================================
// M-Card — boîtier imprimable 3D (V0.1)
// ============================================================
// Pièces (variable `part`) :
//   "shell"          corps principal (imprimer À L'ENVERS, face sup. sur le plateau)
//   "backrest"       dosseret porte-lecteur RFID (imprimer couché sur la face avant)
//   "backrest_cover" plaque arrière du dosseret (à plat)
//   "lid"            fond vissé, avec plots Raspberry Pi (à plat)
//   "assembly"       vue d'ensemble (ne pas imprimer)
//   "print_plate"    toutes les pièces posées à plat (aperçu)
//
// Rendu CLI, exemple :
//   openscad -o stl/shell.stl -D 'part="shell"' mcard.scad
//
// Matériau conseillé : PLA ou PETG, 3 périmètres, remplissage 15 %,
// sans support (le chanfrein de la fente est à 45°).
// ============================================================

part = "assembly";

/* ------------------- paramètres principaux ------------------- */

wall        = 3;      // épaisseur des parois
box_w       = 210;    // largeur externe (X)
box_d       = 130;    // profondeur externe (Y)
box_h       = 95;     // hauteur externe (Z)
corner_r    = 6;      // rayon des angles verticaux

// Fente CD / vinyle (traverse la face supérieure)
slot_len        = 180;   // longueur (X)
slot_w          = 14;    // largeur : boîtier CD 10,4 mm / vinyle avec jeu
slot_depth      = 28;    // profondeur utile sous la face supérieure
slot_center_y   = 20;    // position du centre de la fente (0 = milieu du boîtier)
slot_wall       = 2.5;   // parois du canal interne
slot_chamfer    = 5;     // chanfrein d'entrée à 45°

// Écran LCD 2004A (module 98x60, trous 93x55, fenêtre utile ~97x40)
lcd_window_w    = 99;
lcd_window_h    = 41;
lcd_center_z    = 62;
lcd_hole_dx     = 93;    // entraxe horizontal des vis
lcd_hole_dz     = 55;    // entraxe vertical des vis
lcd_post_d      = 7;
lcd_pilot_d     = 2.8;   // vis M3 auto-taraudée

// Boutons 12 mm à visser
btn_d           = 12.6;
btn_spacing     = 32;
btn_center_z    = 22;

// Embase USB-C panneau (arrière)
usbc_w          = 15;    // découpe oblongue
usbc_h          = 8;
usbc_center_z   = 22;
usbc_screw_dx   = 20;    // entraxe des 2 vis M2
usbc_screw_d    = 2.3;

// Dosseret + lecteur ACR122U (carte nue ~92x60x8 : ajuster ici si besoin)
back_w          = 140;   // largeur du dosseret
back_t          = 24;    // épaisseur
back_h          = 150;   // hauteur au-dessus de la face supérieure
back_r          = 14;    // arrondi du sommet
reader_w        = 95;    // logement carte lecteur (larg.)
reader_h        = 65;    // logement (haut.)
reader_t        = 10;    // logement (prof.)
reader_bottom_z = 12;    // bas du logement au-dessus de la face sup.
cable_hole_w    = 14;    // passage du câble mini-USB vers l'intérieur
cable_hole_d    = 9;

// Assemblage
boss_d          = 10;    // bosses de vissage du fond
pilot_m3        = 2.8;   // avant-trou vis M3 auto-taraudée
lid_screw_d     = 3.4;
lid_t           = 3;
peg_d           = 5;     // pions d'alignement du dosseret
peg_h           = 5;

// Raspberry Pi 3B+ (trous 58 x 49, M2.5)
pi_hole_dx      = 58;
pi_hole_dy      = 49;
pi_post_d       = 6;
pi_pilot_d      = 2.2;
pi_pos          = [-30, -25];  // position du coin de référence des plots sur le fond

fn = 48;
eps = 0.01;

/* ------------------- utilitaires ------------------- */

module rounded_box(w, d, h, r) {
    hull()
        for (x = [-w/2 + r, w/2 - r], y = [-d/2 + r, d/2 - r])
            translate([x, y, 0]) cylinder(r = r, h = h, $fn = fn);
}

// profil 2D du dosseret (plan XZ), sommet arrondi
module backrest_profile() {
    offset(r = back_r, $fn = fn) offset(delta = -back_r)
        square([back_w, back_h + back_r], center = false);
}

/* ------------------- corps principal ------------------- */

module shell() {
    difference() {
        union() {
            // coque
            difference() {
                rounded_box(box_w, box_d, box_h, corner_r);
                translate([0, 0, -eps])
                    rounded_box(box_w - 2*wall, box_d - 2*wall, box_h - wall + eps, corner_r - wall);
            }
            // canal interne de la fente (suspendu sous la face supérieure)
            translate([-slot_len/2 - slot_wall,
                       slot_center_y - slot_w/2 - slot_wall,
                       box_h - wall - slot_depth - slot_wall])
                cube([slot_len + 2*slot_wall, slot_w + 2*slot_wall, slot_depth + slot_wall]);
            // bosses de vissage du fond (ancrées 1 mm dans les parois)
            for (x = [-1, 1], y = [-1, 1])
                translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), 0])
                    cylinder(d = boss_d, h = 14, $fn = fn);
            // plots de fixation du LCD (autour de la fenêtre, côté intérieur)
            for (x = [-1, 1], z = [-1, 1])
                translate([x*lcd_hole_dx/2, -box_d/2 + wall, lcd_center_z + z*lcd_hole_dz/2])
                    rotate([-90, 0, 0]) cylinder(d = lcd_post_d, h = 6, $fn = fn);
        }

        // fente + chanfrein d'entrée
        translate([-slot_len/2, slot_center_y - slot_w/2, box_h - wall - slot_depth])
            cube([slot_len, slot_w, slot_depth + wall + eps]);
        translate([0, slot_center_y, box_h])
            hull() {
                translate([0, 0, eps]) cube([slot_len + 2*slot_chamfer, slot_w + 2*slot_chamfer, eps], center = true);
                translate([0, 0, -slot_chamfer]) cube([slot_len, slot_w, eps], center = true);
            }

        // fenêtre LCD
        translate([0, -box_d/2 - eps, lcd_center_z])
            rotate([-90, 0, 0])
            translate([-lcd_window_w/2, -lcd_window_h/2, 0])
            cube([lcd_window_w, lcd_window_h, wall + 2*eps]);
        // avant-trous des vis LCD
        for (x = [-1, 1], z = [-1, 1])
            translate([x*lcd_hole_dx/2, -box_d/2 + wall + 6 + eps, lcd_center_z + z*lcd_hole_dz/2])
                rotate([90, 0, 0]) cylinder(d = lcd_pilot_d, h = 6 + eps, $fn = fn);

        // boutons (3 : prev, play/pause, next)
        for (i = [-1 : 1])
            translate([i*btn_spacing, -box_d/2 - eps, btn_center_z])
                rotate([-90, 0, 0]) cylinder(d = btn_d, h = wall + 2*eps, $fn = fn);

        // embase USB-C arrière (découpe oblongue + 2 vis)
        translate([0, box_d/2 + eps, usbc_center_z]) rotate([90, 0, 0]) {
            hull()
                for (x = [-1, 1])
                    translate([x*(usbc_w - usbc_h)/2, 0, 0])
                        cylinder(d = usbc_h, h = wall + 2*eps, $fn = fn);
            for (x = [-1, 1])
                translate([x*usbc_screw_dx/2, 0, 0])
                    cylinder(d = usbc_screw_d, h = wall + 2*eps, $fn = fn);
        }

        // avant-trous M3 dans les bosses du fond
        for (x = [-1, 1], y = [-1, 1])
            translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), -eps])
                cylinder(d = pilot_m3, h = 12, $fn = fn);

        // fixation du dosseret : pions + vis M3 depuis l'intérieur
        backrest_fixings(holes = true);
    }
}

// positions communes dosseret <-> face supérieure
function back_front_y() = slot_center_y + slot_w/2 + slot_wall;

module backrest_fixings(holes = false) {
    fy = back_front_y();
    for (x = [-1, 1]) {
        // pions d'alignement
        translate([x*60, fy + back_t/2, box_h - (holes ? peg_h : 0)])
            cylinder(d = peg_d + (holes ? 0.4 : 0), h = peg_h + eps, $fn = fn);
        // vis M3 traversant la face supérieure
        if (holes)
            translate([x*35, fy + back_t/2, box_h - wall - eps])
                cylinder(d = lid_screw_d, h = wall + 2*eps, $fn = fn);
    }
    // passage du câble du lecteur
    if (holes)
        translate([0, fy + 4 + cable_hole_d/2, box_h - wall - eps])
            hull()
                for (x = [-1, 1])
                    translate([x*(cable_hole_w - cable_hole_d)/2, 0, 0])
                        cylinder(d = cable_hole_d, h = wall + 2*eps, $fn = fn);
}

/* ------------------- dosseret ------------------- */

module backrest() {
    fy = back_front_y();
    difference() {
        // volume : profil arrondi extrudé
        translate([-back_w/2, fy, box_h])
            rotate([90, 0, 0]) rotate([0, 0, 0])
            translate([0, 0, -back_t])
            linear_extrude(back_t)
            backrest_profile();

        // logement du lecteur (ouvert vers l'arrière)
        translate([-reader_w/2, fy + wall, box_h + reader_bottom_z])
            cube([reader_w, back_t, reader_h]);

        // passage du câble vers le bas
        translate([0, fy + 4 + cable_hole_d/2, box_h - eps])
            hull()
                for (x = [-1, 1])
                    translate([x*(cable_hole_w - cable_hole_d)/2, 0, 0])
                        cylinder(d = cable_hole_d, h = reader_bottom_z + 2*eps, $fn = fn);

        // avant-trous des vis M3 (depuis l'intérieur du boîtier)
        for (x = [-1, 1])
            translate([x*35, fy + back_t/2, box_h - eps])
                cylinder(d = pilot_m3, h = 10, $fn = fn);

        // avant-trous de la plaque arrière (4 x M3)
        for (x = [-1, 1], z = [0, 1])
            translate([x*(reader_w/2 + 8), fy + back_t + eps,
                       box_h + reader_bottom_z + 6 + z*(reader_h - 12)])
                rotate([90, 0, 0]) cylinder(d = pilot_m3, h = 8, $fn = fn);
    }
    // pions d'alignement sous le dosseret
    for (x = [-1, 1])
        translate([x*60, fy + back_t/2, box_h - peg_h])
            cylinder(d = peg_d, h = peg_h, $fn = fn);
}

module backrest_cover() {
    fy = back_front_y();
    difference() {
        translate([-(reader_w/2 + 14), fy + back_t, box_h + reader_bottom_z - 6])
            cube([reader_w + 28, 2, reader_h + 12]);
        for (x = [-1, 1], z = [0, 1])
            translate([x*(reader_w/2 + 8), fy + back_t + 3,
                       box_h + reader_bottom_z + 6 + z*(reader_h - 12)])
                rotate([90, 0, 0]) cylinder(d = lid_screw_d, h = 4, $fn = fn);
    }
}

/* ------------------- fond ------------------- */

module lid() {
    difference() {
        union() {
            // plaque avec lèvre interne
            translate([0, 0, 0]) rounded_box(box_w - 0.6, box_d - 0.6, lid_t, corner_r);
            translate([0, 0, lid_t - eps])
                difference() {
                    rounded_box(box_w - 2*wall - 0.6, box_d - 2*wall - 0.6, 2.5, corner_r - wall);
                    rounded_box(box_w - 2*wall - 5, box_d - 2*wall - 5, 2.5 + eps, corner_r - wall - 1);
                }
            // plots Raspberry Pi (M2.5 auto-taraudée)
            for (x = [0, 1], y = [0, 1])
                translate([pi_pos[0] + x*pi_hole_dx - pi_hole_dx/2 + pi_hole_dx/2,
                           pi_pos[1] + y*pi_hole_dy - pi_hole_dy/2 + pi_hole_dy/2, lid_t - eps])
                    difference() {
                        cylinder(d = pi_post_d, h = 6, $fn = fn);
                        cylinder(d = pi_pilot_d, h = 6 + eps, $fn = fn);
                    }
        }
        // vis de fixation (fraisées) dans les bosses
        for (x = [-1, 1], y = [-1, 1])
            translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), -eps]) {
                cylinder(d = lid_screw_d, h = lid_t + 2*eps, $fn = fn);
                cylinder(d1 = 6.5, d2 = lid_screw_d, h = 2, $fn = fn);
            }
        // aérations
        for (x = [-4 : 4])
            translate([x*12, 38, -eps])
                hull()
                    for (y = [-1, 1])
                        translate([0, y*8, 0]) cylinder(d = 4, h = lid_t + 2*eps, $fn = 24);
    }
}

/* ------------------- rendu ------------------- */

module assembly() {
    color("WhiteSmoke") shell();
    color("Gainsboro") backrest();
    color("DarkGray") backrest_cover();
    color("LightSteelBlue") translate([0, 0, -12]) lid();
}

if (part == "shell") {
    // à l'envers pour l'impression : face supérieure sur le plateau
    rotate([180, 0, 0]) translate([0, 0, -box_h]) shell();
} else if (part == "backrest") {
    // couché sur la face avant, posé sur le plateau
    fy = back_front_y();
    translate([0, -249.5, -29.5])
        translate([0, box_h + back_h/2, fy + back_t])
        rotate([-90, 0, 0]) translate([0, -(fy), -box_h]) backrest();
} else if (part == "backrest_cover") {
    fy = back_front_y();
    translate([0, 84, 47.5])
        rotate([90, 0, 0]) translate([0, -box_h - reader_bottom_z + 6, -fy - back_t - 2]) backrest_cover();
} else if (part == "lid") {
    lid();
} else if (part == "print_plate") {
    translate([0, -90, box_h]) rotate([180, 0, 0]) shell();
    translate([0, 120, 0]) rotate([90, 0, 0]) translate([0, -box_h, -back_front_y() - back_t]) backrest();
    translate([180, 40, 0]) lid();
    translate([-40, 230, 0]) rotate([90, 0, 0]) translate([0, -box_h - reader_bottom_z + 6, -back_front_y() - back_t - 2]) backrest_cover();
} else {
    assembly();
}
