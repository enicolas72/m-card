// ============================================================
// M-Card — 3D-printable enclosure (V0.3 "magnetic stirrer")
// ============================================================
// V0.3: low base (48 mm) with a SLOPED FRONT console (~34°) carrying the
// LCD + buttons faceplate, like a lab magnetic stirrer.
// Keeps what V0.2 got right: separate faceplate, M3 insert pockets, slot
// running the full length (vinyl), widened USB-A cable passages.
// The Raspberry Pi lies flat BEHIND the slot (hence box_d 150).
//
// Parts (`part` variable):
//   "shell"          main body (print UPSIDE DOWN, top on the bed)
//   "faceplate"      sloped LCD + buttons faceplate (print front face on the bed)
//   "backrest"       RFID reader backrest (print lying on its front face)
//   "backrest_cover" backrest back plate (flat)
//   "icon_plate"     color plate for the icons (flat, contrasting color)
//   "lid"            screwed bottom with Raspberry Pi posts (flat)
//   "assembly"       overall view (do not print)
//
// CLI render: openscad -o stl/shell.stl -D 'part="shell"' mcard.scad
// PLA/PETG, 3 perimeters, 15 %, no supports.
// ============================================================

part = "assembly";

/* ------------------- main parameters ------------------- */

wall        = 3;      // wall thickness
box_w       = 210;    // outer width (X)
box_d       = 150;    // outer depth (Y)
box_h       = 48;     // base height (Z), the "deck"
corner_r    = 6;      // radius of the vertical corners

// Sloped front console
lip         = 10;     // height of the vertical front lip
console_run = 57;     // horizontal depth of the console
// angle of the face from horizontal:
alpha       = atan((box_h - lip)/console_run);          // ~33.7°
face_len    = norm([console_run, box_h - lip]);         // slope length (~68.5)

// CD / vinyl slot, open across the full width, centered at y=0
slot_w          = 14;
slot_depth      = 28;
slot_center_y   = 0;
slot_wall       = 2.5;
slot_chamfer    = 5;

// Hangtife M3x5x4 threaded inserts (OD 5.0, length 4.0):
// recommended hole Ø4.31-4.35, blind min 5.0; printed Ø4.4 ~ 4.3 actual
insert_d        = 4.4;
insert_depth    = 7;     // > min 5: leaves room for the screw tip
insert_cham     = 1.0;   // entry cone: centers the insert (head Ø5.0)
// M3 socket head cap screws (Ø5.5 x 3 head): counterbore, not countersink
screw_cb_d      = 6.2;   // counterbore Ø
screw_cb_h      = 3.2;   // counterbore depth (flush head)

// Faceplate (local frame: x = width, s = along the slope, z = normal to
// the face, 0 = outer surface of the console, +z pointing outward)
face_w          = 200;
plate_s0        = 1.2;   // bottom edge of the plate (s coordinate)
plate_s1        = 67.2;  // top edge
face_t          = 4;     // 4 mm: fits the socket head counterbores
face_r          = 3;
face_screw_x    = 93;
face_screw_s    = [8, 60];
// opening in the sloped wall (lets the LCD + buttons through)
open_x0 = -63;  open_x1 = 75;  open_s0 = 2;  open_s1 = 65.5;

// LCD 2004A (98x60 module, 93x55 holes, ~97x40 visible window)
lcd_center_x    = -10;
lcd_center_s    = 34;
lcd_window_w    = 99;
lcd_window_h    = 41;
lcd_hole_dx     = 93;
lcd_hole_ds     = 55;
lcd_post_d      = 7;
lcd_post_h      = 6;
lcd_pilot_d     = 2.8;

// 12 mm buttons: a column along the slope, right of the screen
btn_d           = 12.6;
btn_x           = 64;
btn_s           = [14, 34, 54];   // bottom ⏮, middle ⏯, top ⏭
// CUT-THROUGH icons: through cut-outs + a color plate glued into a recess
// at the back of the faceplate ("icon_plate" part, contrasting color)
btn_icon_s      = 5;     // glyph size
btn_icon_x      = 80;    // icon column, right of the buttons
icon_pocket_x0  = 72;    // recess at the back of the faceplate
icon_pocket_x1  = 88;
icon_pocket_t   = 2;     // recess depth (remaining front skin: 2 mm)
icon_pocket_r   = 2;     // recess fillets
icon_plate_gap  = 0.2;   // plate clearance per side

// Panel-mount USB-C socket (rear): POWER input
usbc_w          = 15;
usbc_h          = 8;
usbc_center_z   = 22;
usbc_screw_dx   = 20;
usbc_screw_d    = 2.3;

// Backrest + ACR122U reader (bare 60x91 board, IN LANDSCAPE: antenna, the
// large flat area, to the left; cable exiting on the right)
// Full-width trapezoid resting on the base, rounded top corners, mostly
// hollow inside (free cable path), closed by a flush back plate of the
// same shape.
back_w          = box_w; // same width as the base, square bottom
back_t          = 25;    // total thickness (body 21 + plate 4)
back_h          = 84;    // room for the reader in landscape (8 + 62 + cavity margin)
back_top_w      = 126;   // top width (wide enough for the reader in landscape)
back_top_r      = 14;    // top corner radius
back_rim        = 10;    // solid rim around the cavity (holds the inserts)
cover_t         = 4;     // back plate thickness (socket head counterbores)
// back plate screws: positions [x, z above the deck]
cover_screws    = [[93, 10], [66, 58]];  // on the rim centerline (side = tangent to the rounded corner)
reader_w        = 93;    // pocket (width = 91 + clearance, landscape)
reader_h        = 62;    // pocket (height = 60 + clearance)
reader_off_x    = 12;    // reader offset: centers the antenna, cable on the right
reader_bottom_z = 8;
cable_off_x     = 50;    // USB passage offset to the cable side (right)

// Passage for the reader's USB-A cable (molded plug ~16x8 mm)
cable_hole_w    = 18;
cable_hole_d    = 10.5;

// Assembly
boss_d          = 10;
boss_h          = 10;    // limited by the console above the front bosses
lid_screw_d     = 3.4;
lid_t           = 4;     // 4 mm: fits the socket head counterbores
peg_d           = 5;
peg_h           = 5;

// Raspberry Pi 3B+ (58 x 49, M2.5), flat behind the slot
pi_hole_dx      = 58;
pi_hole_dy      = 49;
pi_post_d       = 6;
pi_pilot_d      = 2.2;
pi_pos          = [-30, 19];

fn = 48;
eps = 0.01;

/* ------------------- helpers ------------------- */

module rounded_box(w, d, h, r) {
    hull()
        for (x = [-w/2 + r, w/2 - r], y = [-d/2 + r, d/2 - r])
            translate([x, y, 0]) cylinder(r = r, h = h, $fn = fn);
}

// pocket for an M3 threaded insert (entry at z=0, goes toward +z)
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

// places the children in the sloped-face frame:
// x = width, y = s (along the slope), z = outward normal
module on_face() {
    translate([0, -box_d/2, lip]) rotate([alpha, 0, 0]) children();
}

// prism above the slope line (yz profile), full width
// dz: vertical offset of the line (0 = outer surface)
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

/* ------------------- main body ------------------- */

function back_front_y() = slot_center_y + slot_w/2 + slot_wall;

module shell() {
    inner_dz = -wall * face_len / console_run;  // inner plane (wall thickness = wall, measured normal)
    difference() {
        union() {
            // shell: box - console - inner cavity
            difference() {
                rounded_box(box_w, box_d, box_h, corner_r);
                wedge_cutter(0);
                // inner cavity (below the inner sloped plane)
                difference() {
                    translate([0, 0, -eps])
                        rounded_box(box_w - 2*wall, box_d - 2*wall,
                                    box_h - wall + eps, corner_r - wall);
                    wedge_cutter(inner_dz);
                }
            }
            // inner slot channel, full width
            translate([-box_w/2,
                       slot_center_y - slot_w/2 - slot_wall,
                       box_h - wall - slot_depth - slot_wall])
                cube([box_w, slot_w + 2*slot_wall, slot_depth + slot_wall]);
            // bottom screw bosses
            for (x = [-1, 1], y = [-1, 1])
                translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), 0])
                    cylinder(d = boss_d, h = boss_h, $fn = fn);
            // insert pads behind the sloped wall (faceplate mounting)
            for (x = [-1, 1], is = [0, 1])
                on_face()
                    translate([x*face_screw_x, face_screw_s[is], -wall - 6])
                        cylinder(d = 10, h = 6 + eps, $fn = fn);
        }

        // through slot + chamfer
        translate([-box_w/2 - 1, slot_center_y - slot_w/2, box_h - wall - slot_depth])
            cube([box_w + 2, slot_w, slot_depth + wall + eps]);
        translate([0, slot_center_y, box_h])
            hull() {
                translate([0, 0, eps])
                    cube([box_w + 2, slot_w + 2*slot_chamfer, eps], center = true);
                translate([0, 0, -slot_chamfer])
                    cube([box_w + 2, slot_w, eps], center = true);
            }

        // opening in the sloped face (LCD + buttons)
        on_face()
            translate([open_x0, open_s0, -wall - 4])
                cube([open_x1 - open_x0, open_s1 - open_s0, wall + 8]);

        // faceplate insert pockets (pressed in from the front)
        for (x = [-1, 1], is = [0, 1])
            on_face()
                translate([x*face_screw_x, face_screw_s[is], 0])
                    rotate([180, 0, 0]) insert_pocket();

        // rear USB-C socket (power)
        translate([0, box_d/2 + eps, usbc_center_z]) rotate([90, 0, 0]) {
            oblong(usbc_w, usbc_h, wall + 2*eps);
            for (x = [-1, 1])
                translate([x*usbc_screw_dx/2, 0, 0])
                    cylinder(d = usbc_screw_d, h = wall + 2*eps, $fn = fn);
        }

        // insert pockets in the bottom bosses
        for (x = [-1, 1], y = [-1, 1])
            translate([x*(box_w/2 - wall - boss_d/2 + 1), y*(box_d/2 - wall - boss_d/2 + 1), 0])
                insert_pocket();

        // backrest mounting: pegs + screws + cable passage
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

/* ------------------- faceplate (local face frame) ------------------- */

module faceplate_local() {
    difference() {
        union() {
            // plate (z 0..face_t, resting on the outer surface of the console)
            linear_extrude(face_t)
                offset(r = face_r, $fn = fn) offset(delta = -face_r)
                translate([-face_w/2, plate_s0])
                square([face_w, plate_s1 - plate_s0]);
            // LCD posts, reaching inward through the opening
            for (x = [-1, 1], s = [-1, 1])
                translate([lcd_center_x + x*lcd_hole_dx/2,
                           lcd_center_s + s*lcd_hole_ds/2, -lcd_post_h])
                    cylinder(d = lcd_post_d, h = lcd_post_h + eps, $fn = fn);
        }
        // LCD window
        translate([lcd_center_x - lcd_window_w/2, lcd_center_s - lcd_window_h/2, -eps])
            cube([lcd_window_w, lcd_window_h, face_t + 2*eps]);
        // LCD pilot holes (blind, the front face stays solid)
        for (x = [-1, 1], s = [-1, 1])
            translate([lcd_center_x + x*lcd_hole_dx/2,
                       lcd_center_s + s*lcd_hole_ds/2, -lcd_post_h - eps])
                cylinder(d = lcd_pilot_d, h = lcd_post_h + 1, $fn = fn);
        // buttons
        for (s = btn_s)
            translate([btn_x, s, -eps])
                cylinder(d = btn_d, h = face_t + 2*eps, $fn = fn);
        // recess at the back for the color plate
        translate([0, 0, -eps]) linear_extrude(icon_pocket_t + eps)
            icon_pocket_2d(0);
        // cut-through icons (through the front skin, the color shows)
        for (i = [0 : 2])
            translate([btn_icon_x, btn_s[i], icon_pocket_t - eps])
                linear_extrude(face_t - icon_pocket_t + 2*eps)
                _btn_icon(i);
        // M3 socket head screws -> body inserts (cylindrical counterbore)
        for (x = [-1, 1], is = [0, 1])
            translate([x*face_screw_x, face_screw_s[is], 0]) {
                translate([0, 0, -eps]) cylinder(d = lid_screw_d, h = face_t + 2*eps, $fn = fn);
                translate([0, 0, face_t - screw_cb_h]) cylinder(d = screw_cb_d, h = screw_cb_h + eps, $fn = fn);
            }
        // clearance behind the buttons: panel thinned to 3 mm (thread length)
        for (sb = btn_s)
            translate([btn_x, sb, -eps])
                cylinder(d = 16, h = face_t - 3 + eps, $fn = fn);
    }
}

// 2D outline of the recess / plate (inset > 0: plate clearance)
module icon_pocket_2d(inset) {
    s0 = btn_s[0] - 8;  s1 = btn_s[2] + 8;
    offset(r = icon_pocket_r, $fn = fn) offset(delta = -icon_pocket_r)
        translate([icon_pocket_x0 + inset, s0 + inset])
        square([icon_pocket_x1 - icon_pocket_x0 - 2*inset, s1 - s0 - 2*inset]);
}

// color plate glued into the recess (print in another color)
module icon_plate_local() {
    linear_extrude(icon_pocket_t - 0.2)   // 1.8 mm: flush once glued
        icon_pocket_2d(icon_plate_gap);
}

module faceplate() { on_face() faceplate_local(); }

/* ------------------- backrest ------------------- */

// trapezoid with a square bottom and rounded top corners
module backrest_profile() {
    hull() {
        translate([-back_w/2, 0]) square(eps);
        translate([back_w/2 - eps, 0]) square(eps);
        for (x = [-1, 1])
            translate([x*(back_top_w/2 - back_top_r), back_h - back_top_r])
                circle(r = back_top_r, $fn = fn);
    }
}

// inner cavity: the profile shrunk by back_rim, above the bottom band
module backrest_cavity2d() {
    union() {
        difference() {
            offset(r = -back_rim, $fn = fn) backrest_profile();
            translate([-back_w/2, -1]) square([back_w, reader_bottom_z + 1]);
        }
        // explicit landscape reader pocket (guaranteed whatever the rim)
        translate([reader_off_x - reader_w/2 - 1.5, reader_bottom_z])
            square([reader_w + 3, reader_h + 1]);
    }
}

module backrest() {
    fy = back_front_y();
    body_t = back_t - cover_t;   // the flush back plate completes the thickness
    union() {
        difference() {
            // body
            translate([0, fy, box_h])
                rotate([90, 0, 0])
                translate([0, 0, -body_t])
                linear_extrude(body_t)
                backrest_profile();
            // large cavity (3 mm front wall, open toward the back):
            // holds the reader and lets the cable run freely
            translate([0, fy + wall, box_h])
                rotate([90, 0, 0])
                translate([0, 0, -(body_t - wall + 1)])
                linear_extrude(body_t - wall + 1)
                backrest_cavity2d();
            // cable passage down to the base, right side
            translate([cable_off_x, fy + 4 + cable_hole_d/2, box_h - eps])
                oblong(cable_hole_w, cable_hole_d, reader_bottom_z + 2);
            // insert pockets under the backrest (screws from inside the base)
            for (x = [-1, 1])
                translate([x*35, fy + back_t/2, box_h])
                    insert_pocket();
            // back plate insert pockets (in the rear face of the body)
            for (p = cover_screws, x = [-1, 1])
                translate([x*p[0], fy + body_t, box_h + p[1]])
                    rotate([90, 0, 0]) insert_pocket();
        }
        // positioning stops for the reader board (glued to the front wall)
        for (x = [-1, 1])
            translate([reader_off_x + x*(reader_w/2 + 1) - 1, fy + wall - eps,
                       box_h + reader_bottom_z])
                cube([2, 4 + eps, 30]);
        // alignment pegs under the backrest
        for (x = [-1, 1])
            translate([x*60, fy + back_t/2, box_h - peg_h])
                cylinder(d = peg_d, h = peg_h, $fn = fn);
    }
}

// back plate: same profile as the backrest, flush
module backrest_cover() {
    fy = back_front_y();
    difference() {
        translate([0, fy, box_h])
            rotate([90, 0, 0])
            translate([0, 0, -back_t])   // the plate spans fy+21..fy+25, flush with the body
            linear_extrude(cover_t)
            backrest_profile();
        // M3 socket head screws into the body inserts (cylindrical counterbore)
        for (p = cover_screws, x = [-1, 1])
            translate([x*p[0], fy + back_t + eps, box_h + p[1]])
                rotate([90, 0, 0]) {
                    cylinder(d = lid_screw_d, h = cover_t + 2*eps, $fn = fn);
                    cylinder(d = screw_cb_d, h = screw_cb_h + eps, $fn = fn);
                }
    }
}

/* ------------------- bottom ------------------- */

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
        // vents, under the Raspberry Pi area
        for (x = [-4 : 4])
            translate([x*12, 43, -eps])
                hull()
                    for (y = [-1, 1])
                        translate([0, y*8, 0]) cylinder(d = 4, h = lid_t + 2*eps, $fn = 24);
    }
}

/* ------------------- rendering ------------------- */

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
    // front face (icons) on the bed, posts pointing up
    translate([0, (plate_s0 + plate_s1)/2, face_t])
        rotate([180, 0, 0])
        translate([0, -(plate_s0 + plate_s1)/2, 0])
        faceplate_local();
} else if (part == "backrest") {
    // lying on its front face, on the bed
    // (re-centering constants: check the STL bounds after changing
    //  box_h / back_h / reader_*)
    fy = back_front_y();
    translate([0, -(box_h + back_h/2) + 37.5, fy + back_t])
        translate([0, box_h + back_h/2, -(fy + back_t)])
        rotate([90, 0, 0]) translate([0, -(fy), -box_h]) backrest();
} else if (part == "backrest_cover") {
    fy = back_front_y();
    translate([0, 67, 19.5])
        rotate([90, 0, 0]) translate([0, -box_h - reader_bottom_z + 6, -fy - back_t - 2]) backrest_cover();
} else if (part == "icon_plate") {
    icon_plate_local();
} else if (part == "lid") {
    lid();
} else if (part == "assembly") {
    assembly();
}
