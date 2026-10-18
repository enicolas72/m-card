// Pièces du boîtier en position ASSEMBLÉE (repère de mcard.scad, Z en haut),
// pour le rendu 3D de la page marketing. `include` donne accès à toutes les
// cotes ; `part = "none"` (la dernière affectation l'emporte en OpenSCAD)
// neutralise le sélecteur de pièces de mcard.scad.
include <../../enclosure/mcard.scad>
part = "none";

piece = "shell";

if (piece == "shell") shell();
else if (piece == "faceplate") faceplate();
else if (piece == "icon_plate") on_face() icon_plate_local();
else if (piece == "backrest") backrest();
else if (piece == "backrest_cover") backrest_cover();
else if (piece == "lid") translate([0, 0, -lid_t]) lid();
// module LCD : cadre noir sous la fenêtre + dalle (texturée en JS)
else if (piece == "lcd_bezel")
    on_face() translate([lcd_center_x - 50, lcd_center_s - 21, -2.2]) cube([100, 42, 1.4]);
else if (piece == "lcd_screen")
    on_face() translate([lcd_center_x - 40, lcd_center_s - 13.5, -0.9]) cube([80, 27, 0.3]);
// boutons inox : collerette + poussoir
else if (piece == "buttons")
    on_face() for (s = btn_s) translate([btn_x, s, face_t]) {
        cylinder(d = 15, h = 1.0, $fn = 64);
        cylinder(d = 10.5, h = 1.8, $fn = 64);
    }

// ---- visserie et embase USB-C (comblent les lamages et la découpe arrière)

// tête de vis CHC M3 (Ø5,5 × 3, empreinte hexagonale 2,5), sommet en z = 0,
// corps vers -z ; affleure au fond du lamage
module chc_head() {
    translate([0, 0, -3]) difference() {
        union() {
            cylinder(d = 5.5, h = 2.6, $fn = 48);
            translate([0, 0, 2.6]) cylinder(d1 = 5.5, d2 = 5.0, h = 0.4, $fn = 48);
        }
        translate([0, 0, 1.5]) cylinder(d = 2.5 / cos(30), h = 2, $fn = 6);
    }
}

if (piece == "screws") {
    // façade : 4 vis dans les lamages de la face avant
    on_face() for (x = [-1, 1], s = face_screw_s)
        translate([x*face_screw_x, s, face_t]) chc_head();
    // plaque arrière du dosseret : tête vers +y
    fy = back_front_y();
    for (p = cover_screws, x = [-1, 1])
        translate([x*p[0], fy + back_t, box_h + p[1]]) rotate([-90, 0, 0]) chc_head();
    // fond : tête vers le bas
    for (x = [-1, 1], y = [-1, 1])
        translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), -lid_t])
            rotate([180, 0, 0]) chc_head();
}

// embase USB-C panneau, vue de l'arrière (face externe en y = box_d/2)
module usbc_frame() { translate([0, box_d/2, usbc_center_z]) rotate([-90, 0, 0]) children(); }
if (piece == "usbc_body")       // corps plastique noir qui remplit la découpe
    usbc_frame() translate([0, 0, -wall]) oblong(usbc_w - 0.4, usbc_h - 0.4, wall - 0.5);
else if (piece == "usbc_metal")  // réceptacle + vis M2 à tête cylindrique
    usbc_frame() {
        translate([0, 0, -0.6]) difference() {
            oblong(8.9, 3.3, 0.9);
            translate([0, 0, 0.3]) oblong(8.1, 2.5, 1);
        }
        for (x = [-1, 1]) translate([x*usbc_screw_dx/2, 0, 0]) difference() {
            cylinder(d = 3.8, h = 1.2, $fn = 40);
            translate([0, 0, 0.6]) cube([2.6, 0.5, 1.2], center = true);
        }
    }
else if (piece == "usbc_slot")   // fond sombre de la prise
    usbc_frame() translate([0, 0, -0.35]) oblong(8.1, 2.5, 0.1);
