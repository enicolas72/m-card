// ============================================================
// M-Card — boîtier imprimable 3D (V0.3 « agitateur magnétique »)
// ============================================================
// V0.3 : socle bas (48 mm) avec console AVANT INCLINÉE (~34°) portant la
// façade LCD + boutons, à la manière d'un agitateur magnétique de labo.
// Conserve les acquis V0.2 : façade rapportée, poches à inserts M3, fente
// débouchante toute longueur (vinyle), passages câble USB-A élargis.
// Le Raspberry Pi loge à plat DERRIÈRE la fente (d'où box_d 150).
//
// Pièces (variable `part`) :
//   "shell"          corps principal (imprimer À L'ENVERS, dessus sur le plateau)
//   "faceplate"      façade inclinée LCD + boutons (imprimer face avant sur le plateau)
//   "backrest"       dosseret porte-lecteur RFID (imprimer couché sur la face avant)
//   "backrest_cover" plaque arrière du dosseret (à plat)
//   "lid"            fond vissé, avec plots Raspberry Pi (à plat)
//   "assembly"       vue d'ensemble (ne pas imprimer)
//
// Rendu CLI : openscad -o stl/shell.stl -D 'part="shell"' mcard.scad
// PLA/PETG, 3 périmètres, 15 %, sans support.
// ============================================================

part = "assembly";

/* ------------------- paramètres principaux ------------------- */

wall        = 3;      // épaisseur des parois
box_w       = 210;    // largeur externe (X)
box_d       = 150;    // profondeur externe (Y)
box_h       = 48;     // hauteur du socle (Z) — le « deck »
corner_r    = 6;      // rayon des angles verticaux

// Console avant inclinée
lip         = 10;     // hauteur de la lèvre verticale avant
console_run = 57;     // profondeur horizontale de la console
// angle de la face par rapport à l'horizontale :
alpha       = atan((box_h - lip)/console_run);          // ~33,7°
face_len    = norm([console_run, box_h - lip]);         // longueur de la pente (~68,5)

// Fente CD / vinyle — débouchante sur toute la largeur, centrée en y=0
slot_w          = 14;
slot_depth      = 28;
slot_center_y   = 0;
slot_wall       = 2.5;
slot_chamfer    = 5;

// Inserts filetés M3 Hangtife M3x5x4 (OD 5,0, long. 4,0) :
// trou recommandé Ø4,31-4,35, borgne min 5,0 — Ø4,4 imprimé ~ 4,3 réel
insert_d        = 4.4;
insert_depth    = 7;     // > min 5 : laisse du vide pour le dépassement de vis
insert_cham     = 1.0;   // cône d'entrée : centre l'insert (tête Ø5,0)
// Vis M3 CHC (tête cylindrique Ø5,5 x 3) : lamage, pas de fraisage
screw_cb_d      = 6.2;   // Ø du lamage
screw_cb_h      = 3.2;   // profondeur du lamage (tête affleurante)

// Façade (repère local : x = largeur, s = le long de la pente, z = normale
// à la face, 0 = surface externe de la console, +z vers l'extérieur)
face_w          = 200;
plate_s0        = 1.2;   // bord bas de la plaque (coordonnée s)
plate_s1        = 67.2;  // bord haut
face_t          = 4;     // 4 mm : loge le lamage des têtes CHC
face_r          = 3;
face_screw_x    = 93;
face_screw_s    = [8, 60];
// ouverture dans la paroi inclinée (laisse passer LCD + boutons)
open_x0 = -63;  open_x1 = 75;  open_s0 = 2;  open_s1 = 65.5;

// Écran LCD 2004A (module 98x60, trous 93x55, fenêtre utile ~97x40)
lcd_center_x    = -10;
lcd_center_s    = 34;
lcd_window_w    = 99;
lcd_window_h    = 41;
lcd_hole_dx     = 93;
lcd_hole_ds     = 55;
lcd_post_d      = 7;
lcd_post_h      = 6;
lcd_pilot_d     = 2.8;

// Boutons 12 mm — colonne le long de la pente, à droite de l'écran
btn_d           = 12.6;
btn_x           = 64;
btn_s           = [14, 34, 54];   // bas ⏮, milieu ⏯, haut ⏭
btn_icon_depth  = 0.5;
btn_icon_s      = 4.5;
btn_icon_x      = 78;

// Embase USB-C panneau (arrière) — port d'ALIMENTATION
usbc_w          = 15;
usbc_h          = 8;
usbc_center_z   = 22;
usbc_screw_dx   = 20;
usbc_screw_d    = 2.3;

// Dosseret + lecteur ACR122U (carte nue 60x91, EN PAYSAGE : antenne — la
// grande zone plane — vers la gauche, câble sortant à droite)
// Trapèze pleine largeur épaulé sur le socle, coins hauts arrondis,
// intérieur globalement creux (passage de câble libre), fermé par une
// plaque arrière de même forme, affleurante.
back_w          = box_w; // même largeur que le socle, base d'équerre
back_t          = 25;    // épaisseur totale (corps 21 + plaque 4)
back_h          = 84;    // place du lecteur en paysage (8 + 62 + marge cavité)
back_top_w      = 90;    // largeur du sommet
back_top_r      = 14;    // rayon des coins hauts
back_rim        = 10;    // pourtour plein autour de la cavité (loge les inserts)
cover_t         = 4;     // épaisseur de la plaque arrière (lamages CHC)
// vis de la plaque arrière : positions [x, z au-dessus du deck]
cover_screws    = [[90, 10], [52, 58]];  // dans l'axe du pourtour (flanc = tangente au coin arrondi)
reader_w        = 93;    // logement (larg. = 91 + jeu, paysage)
reader_h        = 62;    // logement (haut. = 60 + jeu)
reader_off_x    = 12;    // décalage du lecteur : recentre l'antenne, câble à droite
reader_bottom_z = 8;
cable_off_x     = 50;    // passage USB décalé côté câble (droite)

// Passage du câble USB-A du lecteur (prise surmoulée ~16x8 mm)
cable_hole_w    = 18;
cable_hole_d    = 10.5;

// Assemblage
boss_d          = 10;
boss_h          = 10;    // limité par la console au-dessus des bosses avant
lid_screw_d     = 3.4;
lid_t           = 4;     // 4 mm : loge le lamage des têtes CHC
peg_d           = 5;
peg_h           = 5;

// Raspberry Pi 3B+ (58 x 49, M2.5) — à plat derrière la fente
pi_hole_dx      = 58;
pi_hole_dy      = 49;
pi_post_d       = 6;
pi_pilot_d      = 2.2;
pi_pos          = [-30, 19];

fn = 48;
eps = 0.01;

/* ------------------- utilitaires ------------------- */

module rounded_box(w, d, h, r) {
    hull()
        for (x = [-w/2 + r, w/2 - r], y = [-d/2 + r, d/2 - r])
            translate([x, y, 0]) cylinder(r = r, h = h, $fn = fn);
}

// poche pour insert fileté M3 (entrée en z=0, s'enfonce en +z)
module insert_pocket() {
    translate([0, 0, -eps]) {
        cylinder(d = insert_d, h = insert_depth + eps, $fn = fn);
        cylinder(d1 = insert_d + 2*insert_cham, d2 = insert_d,
                 h = insert_cham + eps, $fn = fn);
    }
}

module oblong(w, d, h) {
    hull()
        for (x = [-1, 1])
            translate([x*(w - d)/2, 0, 0]) cylinder(d = d, h = h, $fn = fn);
}

module _tri(s, dir) { polygon([[0, -s/2], [0, s/2], [dir*0.87*s, 0]]); }
module _icon_prev(s) {
    translate([0.1*s, 0]) {
        translate([-1.1*s, -s/2]) square([0.22*s, s]);
        _tri(s, -1);
        translate([0.9*s, 0]) _tri(s, -1);
    }
}
module _icon_next(s) { mirror([1, 0]) _icon_prev(s); }
module _icon_playpause(s) {
    translate([0.14*s, 0]) {
        translate([-1.05*s, 0]) _tri(s, 1);
        translate([0.15*s, -s/2]) square([0.22*s, s]);
        translate([0.55*s, -s/2]) square([0.22*s, s]);
    }
}
module _btn_icon(i) {
    if (i == 0) _icon_prev(btn_icon_s);
    else if (i == 1) _icon_playpause(btn_icon_s);
    else _icon_next(btn_icon_s);
}

// place les enfants dans le repère de la face inclinée :
// x = largeur, y = s (le long de la pente), z = normale externe
module on_face() {
    translate([0, -box_d/2, lip]) rotate([alpha, 0, 0]) children();
}

// prisme au-dessus de la ligne de pente (profil yz), pleine largeur
// dz : décalage vertical de la ligne (0 = surface externe)
module wedge_cutter(dz = 0) {
    m = (box_h - lip)/console_run;
    translate([-(box_w/2 + 5), 0, 0])
        rotate([90, 0, 90])
        linear_extrude(box_w + 10)
        polygon([
            [-box_d/2 - 40, lip + dz],
            [-box_d/2, lip + dz],
            [box_d/2 + 40, lip + dz + m*(box_d + 40)],
            [box_d/2 + 40, 400],
            [-box_d/2 - 40, 400],
        ]);
}

/* ------------------- corps principal ------------------- */

function back_front_y() = slot_center_y + slot_w/2 + slot_wall;

module shell() {
    inner_dz = -wall * face_len / console_run;  // plan interne (paroi normale = wall)
    difference() {
        union() {
            // coque : boîte - console - cavité interne
            difference() {
                rounded_box(box_w, box_d, box_h, corner_r);
                wedge_cutter(0);
                // cavité interne (sous le plan incliné interne)
                difference() {
                    translate([0, 0, -eps])
                        rounded_box(box_w - 2*wall, box_d - 2*wall,
                                    box_h - wall + eps, corner_r - wall);
                    wedge_cutter(inner_dz);
                }
            }
            // canal interne de la fente — toute la largeur
            translate([-box_w/2,
                       slot_center_y - slot_w/2 - slot_wall,
                       box_h - wall - slot_depth - slot_wall])
                cube([box_w, slot_w + 2*slot_wall, slot_depth + slot_wall]);
            // bosses de vissage du fond
            for (x = [-1, 1], y = [-1, 1])
                translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), 0])
                    cylinder(d = boss_d, h = boss_h, $fn = fn);
            // pastilles à insert derrière la paroi inclinée (fixation façade)
            for (x = [-1, 1], is = [0, 1])
                on_face()
                    translate([x*face_screw_x, face_screw_s[is], -wall - 6])
                        cylinder(d = 10, h = 6 + eps, $fn = fn);
        }

        // fente débouchante + chanfrein
        translate([-box_w/2 - 1, slot_center_y - slot_w/2, box_h - wall - slot_depth])
            cube([box_w + 2, slot_w, slot_depth + wall + eps]);
        translate([0, slot_center_y, box_h])
            hull() {
                translate([0, 0, eps])
                    cube([box_w + 2, slot_w + 2*slot_chamfer, eps], center = true);
                translate([0, 0, -slot_chamfer])
                    cube([box_w + 2, slot_w, eps], center = true);
            }

        // ouverture de la face inclinée (LCD + boutons)
        on_face()
            translate([open_x0, open_s0, -wall - 4])
                cube([open_x1 - open_x0, open_s1 - open_s0, wall + 8]);

        // poches à inserts de la façade (pressés depuis l'avant)
        for (x = [-1, 1], is = [0, 1])
            on_face()
                translate([x*face_screw_x, face_screw_s[is], 0])
                    rotate([180, 0, 0]) insert_pocket();

        // embase USB-C arrière (alimentation)
        translate([0, box_d/2 + eps, usbc_center_z]) rotate([90, 0, 0]) {
            oblong(usbc_w, usbc_h, wall + 2*eps);
            for (x = [-1, 1])
                translate([x*usbc_screw_dx/2, 0, 0])
                    cylinder(d = usbc_screw_d, h = wall + 2*eps, $fn = fn);
        }

        // poches à inserts des bosses du fond
        for (x = [-1, 1], y = [-1, 1])
            translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), 0])
                insert_pocket();

        // fixation du dosseret : pions + vis + passage câble
        backrest_fixings(holes = true);
    }
}

module backrest_fixings(holes = false) {
    fy = back_front_y();
    for (x = [-1, 1]) {
        translate([x*60, fy + back_t/2, box_h - (holes ? peg_h : 0)])
            cylinder(d = peg_d + (holes ? 0.4 : 0), h = peg_h + eps, $fn = fn);
        if (holes)
            translate([x*35, fy + back_t/2, box_h - wall - eps])
                cylinder(d = lid_screw_d, h = wall + 2*eps, $fn = fn);
    }
    if (holes)
        translate([cable_off_x, fy + 4 + cable_hole_d/2, box_h - wall - eps])
            oblong(cable_hole_w, cable_hole_d, wall + 2*eps);
}

/* ------------------- façade (repère local de la face) ------------------- */

module faceplate_local() {
    difference() {
        union() {
            // plaque (z 0..3, posée sur la surface externe de la console)
            linear_extrude(face_t)
                offset(r = face_r, $fn = fn) offset(delta = -face_r)
                translate([-face_w/2, plate_s0])
                square([face_w, plate_s1 - plate_s0]);
            // plots LCD, traversent l'ouverture vers l'intérieur
            for (x = [-1, 1], s = [-1, 1])
                translate([lcd_center_x + x*lcd_hole_dx/2,
                           lcd_center_s + s*lcd_hole_ds/2, -lcd_post_h])
                    cylinder(d = lcd_post_d, h = lcd_post_h + eps, $fn = fn);
        }
        // fenêtre LCD
        translate([lcd_center_x - lcd_window_w/2, lcd_center_s - lcd_window_h/2, -eps])
            cube([lcd_window_w, lcd_window_h, face_t + 2*eps]);
        // avant-trous LCD (borgnes, la face avant reste pleine)
        for (x = [-1, 1], s = [-1, 1])
            translate([lcd_center_x + x*lcd_hole_dx/2,
                       lcd_center_s + s*lcd_hole_ds/2, -lcd_post_h - eps])
                cylinder(d = lcd_pilot_d, h = lcd_post_h + 1, $fn = fn);
        // boutons
        for (s = btn_s)
            translate([btn_x, s, -eps])
                cylinder(d = btn_d, h = face_t + 2*eps, $fn = fn);
        // icônes gravées dans la face avant (z = face_t)
        for (i = [0 : 2])
            translate([btn_icon_x, btn_s[i], face_t - btn_icon_depth])
                linear_extrude(btn_icon_depth + eps)
                _btn_icon(i);
        // vis CHC M3 -> inserts du corps (lamage cylindrique)
        for (x = [-1, 1], is = [0, 1])
            translate([x*face_screw_x, face_screw_s[is], 0]) {
                translate([0, 0, -eps]) cylinder(d = lid_screw_d, h = face_t + 2*eps, $fn = fn);
                translate([0, 0, face_t - screw_cb_h]) cylinder(d = screw_cb_d, h = screw_cb_h + eps, $fn = fn);
            }
        // dégagement au dos des boutons : panneau ramené à 3 mm (course du filetage)
        for (sb = btn_s)
            translate([btn_x, sb, -eps])
                cylinder(d = 16, h = face_t - 3 + eps, $fn = fn);
    }
}

module faceplate() { on_face() faceplate_local(); }

/* ------------------- dosseret ------------------- */

// trapèze à base d'équerre et coins hauts arrondis
module backrest_profile() {
    hull() {
        translate([-back_w/2, 0]) square(eps);
        translate([back_w/2 - eps, 0]) square(eps);
        for (x = [-1, 1])
            translate([x*(back_top_w/2 - back_top_r), back_h - back_top_r])
                circle(r = back_top_r, $fn = fn);
    }
}

// cavité interne : le profil rétréci de back_rim, au-dessus de la bande basse
module backrest_cavity2d() {
    difference() {
        offset(r = -back_rim, $fn = fn) backrest_profile();
        translate([-back_w/2, -1]) square([back_w, reader_bottom_z + 1]);
    }
}

module backrest() {
    fy = back_front_y();
    body_t = back_t - cover_t;   // la plaque arrière affleurante complète l'épaisseur
    union() {
        difference() {
            // corps
            translate([0, fy, box_h])
                rotate([90, 0, 0])
                translate([0, 0, -body_t])
                linear_extrude(body_t)
                backrest_profile();
            // grande cavité (paroi avant 3 mm, ouverte vers l'arrière) :
            // loge le lecteur et laisse le câble circuler librement
            translate([0, fy + wall, box_h])
                rotate([90, 0, 0])
                translate([0, 0, -(body_t - wall + 1)])
                linear_extrude(body_t - wall + 2)
                backrest_cavity2d();
            // passage du câble vers le socle, côté droit
            translate([cable_off_x, fy + 4 + cable_hole_d/2, box_h - eps])
                oblong(cable_hole_w, cable_hole_d, reader_bottom_z + 2*eps);
            // poches à inserts sous le dosseret (vis venant de l'intérieur du socle)
            for (x = [-1, 1])
                translate([x*35, fy + back_t/2, box_h])
                    insert_pocket();
            // poches à inserts de la plaque arrière (dans la face arrière du corps)
            for (p = cover_screws, x = [-1, 1])
                translate([x*p[0], fy + body_t, box_h + p[1]])
                    rotate([90, 0, 0]) insert_pocket();
        }
        // butées de positionnement de la carte lecteur (collée en face avant)
        for (x = [-1, 1])
            translate([reader_off_x + x*(reader_w/2 + 1) - 1, fy + wall - eps,
                       box_h + reader_bottom_z])
                cube([2, 4 + eps, 30]);
        // pions d'alignement sous le dosseret
        for (x = [-1, 1])
            translate([x*60, fy + back_t/2, box_h - peg_h])
                cylinder(d = peg_d, h = peg_h, $fn = fn);
    }
}

// plaque arrière : même profil que le dosseret, affleurante
module backrest_cover() {
    fy = back_front_y();
    difference() {
        translate([0, fy, box_h])
            rotate([90, 0, 0])
            translate([0, 0, -back_t])   // la plaque occupe fy+21..fy+24, affleurante au corps
            linear_extrude(cover_t)
            backrest_profile();
        // vis CHC M3 vers les inserts du corps (lamage cylindrique)
        for (p = cover_screws, x = [-1, 1])
            translate([x*p[0], fy + back_t + eps, box_h + p[1]])
                rotate([90, 0, 0]) {
                    cylinder(d = lid_screw_d, h = cover_t + 2*eps, $fn = fn);
                    cylinder(d = screw_cb_d, h = screw_cb_h + eps, $fn = fn);
                }
    }
}

/* ------------------- fond ------------------- */

module lid() {
    difference() {
        union() {
            rounded_box(box_w - 0.6, box_d - 0.6, lid_t, corner_r);
            translate([0, 0, lid_t - eps])
                difference() {
                    rounded_box(box_w - 2*wall - 0.6, box_d - 2*wall - 0.6, 2.5, corner_r - wall);
                    rounded_box(box_w - 2*wall - 5, box_d - 2*wall - 5, 2.5 + eps, corner_r - wall - 1);
                }
            for (x = [0, 1], y = [0, 1])
                translate([pi_pos[0] + x*pi_hole_dx, pi_pos[1] + y*pi_hole_dy, lid_t - eps])
                    difference() {
                        cylinder(d = pi_post_d, h = 6, $fn = fn);
                        cylinder(d = pi_pilot_d, h = 6 + eps, $fn = fn);
                    }
        }
        for (x = [-1, 1], y = [-1, 1])
            translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), -eps]) {
                cylinder(d = lid_screw_d, h = lid_t + 2*eps, $fn = fn);
                cylinder(d = screw_cb_d, h = screw_cb_h + eps, $fn = fn);
            }
        // aérations, sous la zone du Raspberry Pi
        for (x = [-4 : 4])
            translate([x*12, 43, -eps])
                hull()
                    for (y = [-1, 1])
                        translate([0, y*8, 0]) cylinder(d = 4, h = lid_t + 2*eps, $fn = 24);
    }
}

/* ------------------- rendu ------------------- */

module assembly() {
    color("WhiteSmoke") shell();
    color("LightSlateGray") faceplate();
    color("Gainsboro") backrest();
    color("DarkGray") backrest_cover();
    color("LightSteelBlue") translate([0, 0, -12]) lid();
}

if (part == "shell") {
    rotate([180, 0, 0]) translate([0, 0, -box_h]) shell();
} else if (part == "faceplate") {
    // face avant (gravures) sur le plateau, plots vers le haut
    translate([0, (plate_s0 + plate_s1)/2, face_t])
        rotate([180, 0, 0])
        translate([0, -(plate_s0 + plate_s1)/2, 0])
        faceplate_local();
} else if (part == "backrest") {
    // couché sur la face avant, posé sur le plateau
    // (constantes de recentrage : vérifier les bornes du STL après
    //  modification de box_h / back_h / reader_*)
    fy = back_front_y();
    translate([0, -(box_h + back_h/2) + 37.5, fy + back_t])
        translate([0, box_h + back_h/2, -(fy + back_t)])
        rotate([90, 0, 0]) translate([0, -(fy), -box_h]) backrest();
} else if (part == "backrest_cover") {
    fy = back_front_y();
    translate([0, 67, 19.5])
        rotate([90, 0, 0]) translate([0, -box_h - reader_bottom_z + 6, -fy - back_t - 2]) backrest_cover();
} else if (part == "lid") {
    lid();
} else {
    assembly();
}
