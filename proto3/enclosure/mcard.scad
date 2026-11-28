// ============================================================
// M-Card proto 3 — 3D-printable enclosure (V1.0)
// ============================================================
// A flat 190 x 96 x 50 mm box, after Eric's sketch (2026-11-22):
//   - card slot on the left of the top: the card stands in portrait,
//     32 mm deep, facing the front;
//   - PN532 reader standing inside, just behind the card, parallel to it;
//   - the screen and the buttons centered in the space right of the card;
//   - 3.12" OLED at the back right of the top, the prev / play-pause /
//     next buttons in a row in front of it (12 mm, as on proto 2); their
//     icons are raised glyphs of a contrasting plate glued under the top,
//     through the top, 0.1 mm proud;
//   - "M." logo the same way: letters on a backing plate glued inside the
//     front wall, through it, 0.1 mm proud (no glue on the visible face).
//
// Two main parts. The TRAY is the floor and the walls (Raspberry Pi
// posts, rear USB-C, logo hole). The COVER is the whole top: card slot,
// reader bay, OLED window and posts, buttons, icons. Everything that has
// wires sits on the cover: wire it on the bench, plug the wires into the
// Pi, lower the cover onto the tray, 4 screws from below.
// (A separate screen plate would have to sit proud of the top, or rest on
// ledges that cannot print without supports: making the whole top the
// plate keeps the box at 50 mm and every part prints support-free.)
//
// Parts (`part` variable):
//   "tray"        floor on the bed
//   "cover"       upside down (top face on the bed)
//   "icon_plate"  plate down, contrasting color: glued into the recess under the
//                 icons, its glyphs through the top (print at 0.1 mm layers)
//   "logo"        plate down, contrasting color: glued inside the front wall,
//                 its letters through it (print at 0.1 mm layers)
//   "assembly"    overall view with dummy components (do not print)
//   "exploded"    the same, cover lifted
//
// Coordinates: origin at the front-left-bottom corner, x to the right,
// y toward the back, z up (mm).
// CLI: openscad -o stl/cover.stl -D 'part="cover"' mcard.scad
// PLA/PETG, 3 perimeters, 15 %, no supports.
// ============================================================

include <logo.scad>

part = "assembly";

/* ------------------- box ------------------- */

box_w       = 190;    // outer width (x)
box_d       = 96;     // outer depth (y)
box_h       = 50;     // total height, cover included
wall        = 3;      // tray walls
corner_r    = 6;      // vertical corner radius
floor_t     = 4;      // tray floor (4 mm: room for the screw counterbores)
top_t       = 3;      // cover top skin (12 mm buttons: panel <= 3 mm)
seam_z      = box_h - top_t;   // top of the tray walls = underside of the cover skin
edge_ch     = 1;      // chamfer on the cover's top outer edge

// cover alignment rim, inside the tray walls
rim_h       = 4;
rim_t       = 1.6;
rim_gap     = 0.3;

/* ------------------- card slot ------------------- */

// ISO card 85.6 x 54 x 0.76, standing in portrait
slot_len    = 56;     // card width 54 + clearance
slot_gap    = 2.0;    // narrow vertical slots print ~0.3 under size
slot_depth  = 32;     // from the top surface to the card's bottom edge
slot_cx     = 36;     // slot center
slot_cy     = 48;     // mid-depth
slot_wall   = 1.6;    // channel walls; the back one carries the reader
slot_ch     = 1.5;    // entry chamfer

slot_floor_z = box_h - slot_depth;   // the card's bottom edge (z 18)

/* ------------------- PN532 reader ------------------- */

// PN532 V3 board (red, measured on Eric's module 2026-11-22): 42.7 x 40.4,
// 4-pin RIGHT-ANGLE header on a 40.4 mm edge, its pins 2.3 mm past the
// edge (45 overall); the Dupont plugs lie over the component side.
// Standing behind the slot, flat (solder) side taped against the slot's
// back wall (antenna ~3 mm from the card), header edge toward the screen
// (+x), DIP switch down. The plugs stick out sideways, between the board
// and the Pi's USB block, then the wires bend up. Held by foam tape and
// positioned by two side stops and a bottom ledge, outside the board
// outline; the right stop is cut around the header.
reader_w    = 42.7;   // horizontal
reader_h    = 40.4;   // vertical: the header edge (the interior is 43 mm: this way up only)
reader_t    = 1.6;    // PCB
reader_tape = 1.0;    // double-sided foam tape
reader_top_gap = 0.5; // board top to the cover skin
reader_clear = 0.4;   // per side, between the board and the stops
stop_t      = 2;      // side stop thickness
stop_d      = 4.5;    // how far the stops and the ledge reach behind the backplate
ledge_t     = 1.6;
hdr_z       = 22.0;   // header center below the board's top edge, as mounted (photo, +-1)
hdr_len     = 10.2;   // 4 x 2.54: the four plugs side by side
hdr_inset   = 3.3;    // the plugs start this far inside the board edge
plug_len    = 14;     // Dupont housing
plug_bend   = 6;      // room for the wires to bend after the plugs
reader_comp_t = 4;    // components, header body and plugs on the component side
stop_cut    = 3;      // right stop cut-out: header +- this (photo estimate)

/* ------------------- OLED (Audiophonics 3.12" 256x64, ref. 14604) ------------------- */

// From the Audiophonics dimension drawing. Module coordinates (u, v):
// u from the left edge, v from the "top" edge, display side facing you,
// 2x8 header CN1 on the right. Mounted glass up under the cover, its top
// edge toward the back (if the picture comes out upside down:
// `oled.rotate: 2` in mcard.yaml).
oled_w      = 100.5;
oled_d      = 33.5;
oled_pcb_t  = 1.0;
oled_glass_t = 2.8;   // PCB front face to glass front face
oled_gap    = 0.3;    // glass to the cover skin
oled_holes  = [[2.25, 2.5], [97.25, 2.5], [2.25, 31.0], [97.25, 31.0]];
oled_va     = [10.35, 4.40, 78.8, 21.18];   // visible area: u, v, w, h
oled_x0     = 77;     // module left edge (box x): window centered right of the card
oled_y1     = 83.5;   // module top edge (box y)
oled_post_d = 5;
oled_pilot_d = 2.2;   // M2.5 screws through the module's holes, tapped into the PLA
win_margin  = 0.6;    // window around the visible area
win_ch      = 1.5;    // window chamfer (wider viewing angle)

oled_post_h = oled_glass_t + oled_gap;
function oled_pt(u, v) = [oled_x0 + u, oled_y1 - v];

/* ------------------- buttons and icons ------------------- */

btn_d       = 12.6;   // 12 mm panel-mount momentary buttons
btn_y       = 34;
btn_x       = [107, 129, 151];   // ⏮ ⏯ ⏭, left to right
btn_nut_r   = 8.5;    // nut footprint under the skin: keep clear
icon_s      = 5;      // glyph size
icon_dy     = 12.5;   // icon center in front of the button center
icon_recess_t = 1.6;  // recess under the icons: 1.4 of skin left (7 layers of 0.2)
icon_half_h = 4;      // recess half-height (the button nuts start 0.5 behind it)
icon_plate_gap = 0.4; // plate clearance per side, in the recess (the glyphs locate it)
icon_gap    = 0.15;   // hole clearance per side around the glyph shape, in the skin
icon_fit    = 0.1;    // plate glyphs a bit thinner still: printed holes come out small
icon_tip_r  = 0.5;    // plate glyph triangles rounded: their 60 deg tips are where the
                      // printed holes close up first (a hole shrinking by e loses 2 e there)
icon_proud  = 0.1;    // the raised glyphs stand out of the top by this much
fill_gaps   = 0.45;   // gaps and corners under 2 x this in the raised shapes are filled:
                      // what is left of the skin between the holes stays printable

icon_y = btn_y - icon_dy;
icon_plate_t = icon_recess_t - 0.2;                // seated against the recess ceiling
icon_glyph_h = top_t - icon_recess_t + icon_proud;  // glyphs above the plate

/* ------------------- logo ------------------- */

// The letters stand on a backing plate glued inside the front wall and go
// through a logo-shaped hole in it: the glue stays out of sight.
logo_w      = 50;     // logo width on the front face (height = logo_w * logo_aspect)
logo_cx     = slot_cx + 2;  // under the card; the plate clears the front-left boss
logo_cz     = box_h/2;
logo_proud  = 0.1;    // the letters stand out of the front face by this much
logo_bold   = 0.2;    // thickens the strokes: the flourish's tip stays printable
logo_gap    = 0.15;   // hole clearance per side around the letter shape
logo_fit    = 0.1;    // printed letters a bit thinner still: 0.25 per side in all
                      // (no tip rounding needed: logo_bold already rounds them)
logo_dot_shift = [0.24, -0.26];   // the dot, 0.35 mm farther from the tail (1.14 mm apart
                                  // on the artwork): 0.8 mm of wall between their holes
logo_plate_t = 1.2;   // backing plate
logo_plate_m = 3;     // plate margin around the letters (the glue goes there)

/* ------------------- Raspberry Pi 3 ------------------- */

// 85 x 56, M2.5 holes 58 x 49. Turned 180°: USB/Ethernet to the left,
// GPIO header along the front, power (micro-USB) at the back.
pi_l        = 85;
pi_wd       = 56;
pi_x0       = 77;     // PCB corner (box coordinates): USB block clear of the reader's plugs
pi_y0       = 6;     // 3 mm behind the front wall: GPIO plugs clear of the cover rim
pi_post_h   = 4;
pi_post_d   = 6;
pi_pilot_d  = 2.2;
pi_holes_std = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];
function pi_holes() = [for (h = pi_holes_std) [pi_x0 + pi_l - h[0], pi_y0 + pi_wd - h[1]]];
pi_z0       = floor_t + pi_post_h;   // PCB underside

/* ------------------- rear USB-C power socket ------------------- */

usbc_x      = 125;
usbc_z      = 22;
usbc_w      = 15;
usbc_h      = 8;
usbc_screw_dx = 20;
usbc_screw_d  = 2.3;

/* ------------------- screws ------------------- */

// Hangtife M3x5x4 threaded inserts (same as proto 2)
insert_d    = 4.4;
insert_depth = 7;
insert_cham = 1.0;
screw_d     = 3.4;
screw_cb_d  = 6.2;    // M3 socket head counterbore
screw_cb_h  = 3.2;
boss_d      = 9;
boss_inset  = wall + boss_d/2 + 0.5;
boss_pos    = [[boss_inset, boss_inset], [box_w - boss_inset, boss_inset],
               [boss_inset, box_d - boss_inset], [box_w - boss_inset, box_d - boss_inset]];
boss_z0     = floor_t + 0.5;   // the screw pulls the cover down onto the walls

fn = 48;
eps = 0.01;

/* ------------------- helpers ------------------- */

module rbox(x0, y0, w, d, h, r) {
    translate([x0, y0, 0]) hull()
        for (x = [r, w - r], y = [r, d - r])
            translate([x, y, 0]) cylinder(r = r, h = h, $fn = fn);
}

// pocket for an M3 threaded insert (entry at z=0, goes toward +z)
module insert_pocket() {
    translate([0, 0, -eps]) {
        cylinder(d = insert_d, h = insert_depth + eps, $fn = fn);
        cylinder(d1 = insert_d + 2*insert_cham, d2 = insert_d, h = insert_cham + eps, $fn = fn);
    }
}

module oblong(w, d, h) {
    hull() for (x = [-1, 1]) translate([x*(w - d)/2, 0, 0]) cylinder(d = d, h = h, $fn = fn);
}

// morphological closing: fills gaps and inner corners narrower than 2 r
module closed(r) { offset(r = -r, $fn = 16) offset(r = r, $fn = 16) children(); }

// the raised letters (strokes slightly thickened); extra > 0: their hole.
// The stroke's own narrow gaps are filled; the dot stays apart.
module logo_shape(extra = 0) {
    offset(r = extra, $fn = 16) union() {
        closed(fill_gaps) offset(r = logo_bold, $fn = 16) logo_part_2d(0, logo_w);
        translate(logo_dot_shift) offset(r = logo_bold, $fn = 16) logo_part_2d(1, logo_w);
    }
}

// $tip_r > 0: corners rounded (the plate's glyphs; the holes keep sharp tips)
$tip_r = 0;
module _tri(s, dir) {
    if ($tip_r > 0) offset(r = $tip_r, $fn = 16) offset(delta = -$tip_r) _tri0(s, dir);
    else _tri0(s, dir);
}
module _tri0(s, dir) { polygon([[0, -s/2], [0, s/2], [dir*0.87*s, 0]]); }
module _icon_prev(s) {
    translate([0.1*s, 0]) {
        translate([-1.1*s, -s/2]) square([0.22*s, s]);
        _tri(s, -1);
        translate([0.9*s, 0]) _tri(s, -1);
    }
}
module _icon_next(s) { mirror([1, 0]) _icon_prev(s); }
module _icon_playpause(s) {   // bars 0.22 s apart: 0.8 mm of skin between their holes
    translate([0.12*s, 0]) {
        translate([-1.05*s, 0]) _tri(s, 1);
        translate([0.15*s, -s/2]) square([0.22*s, s]);
        translate([0.59*s, -s/2]) square([0.22*s, s]);
    }
}
module _btn_icon(i) {
    closed(fill_gaps)
        if (i == 0) _icon_prev(icon_s);
        else if (i == 1) _icon_playpause(icon_s);
        else _icon_next(icon_s);
}

// outline of the recess under the icons (inset > 0: the plate)
module icon_recess_2d(inset = 0) {
    x0 = btn_x[0] - 9;  x1 = btn_x[2] + 9;
    offset(r = 2, $fn = fn) offset(delta = -2)
        translate([x0 + inset, icon_y - icon_half_h + inset])
        square([x1 - x0 - 2*inset, 2*icon_half_h - 2*inset]);
}

/* ------------------- tray ------------------- */

module tray() {
    difference() {
        union() {
            difference() {
                rbox(0, 0, box_w, box_d, seam_z, corner_r);
                translate([0, 0, floor_t])
                    rbox(wall, wall, box_w - 2*wall, box_d - 2*wall, seam_z, corner_r - wall);
            }
            for (h = pi_holes())
                translate([h[0], h[1], floor_t - eps])
                    cylinder(d = pi_post_d, h = pi_post_h + eps, $fn = fn);
        }
        // Raspberry Pi pilot holes (M2.5 x 6, tapped into the PLA)
        for (h = pi_holes())
            translate([h[0], h[1], floor_t - 1])
                cylinder(d = pi_pilot_d, h = pi_post_h + 1 + eps, $fn = fn);
        // cover screws: through the floor, counterbored underneath
        for (p = boss_pos)
            translate([p[0], p[1], -eps]) {
                cylinder(d = screw_d, h = floor_t + 2*eps, $fn = fn);
                cylinder(d = screw_cb_d, h = screw_cb_h + eps, $fn = fn);
            }
        // rear USB-C socket (power)
        translate([usbc_x, box_d + eps, usbc_z]) rotate([90, 0, 0]) {
            oblong(usbc_w, usbc_h, wall + 2*eps);
            for (x = [-1, 1])
                translate([x*usbc_screw_dx/2, 0, 0])
                    cylinder(d = usbc_screw_d, h = wall + 2*eps, $fn = fn);
        }
        // logo hole through the front wall (the letters come through from inside)
        translate([logo_cx, wall + eps, logo_cz]) rotate([90, 0, 0])
            linear_extrude(wall + 2*eps) logo_shape(logo_gap);
        // vents under the Raspberry Pi
        for (i = [0 : 7])
            translate([pi_x0 + 11 + 9*i, pi_y0 + pi_wd/2, -eps])
                rotate([0, 0, 90]) oblong(30, 4, floor_t + 2*eps);
    }
}

/* ------------------- cover ------------------- */

module top_skin() {
    hull() {
        translate([0, 0, seam_z])
            rbox(0, 0, box_w, box_d, top_t - edge_ch, corner_r);
        translate([0, 0, seam_z])
            rbox(edge_ch, edge_ch, box_w - 2*edge_ch, box_d - 2*edge_ch, top_t, corner_r - edge_ch);
    }
}

module rim() {
    o = wall + rim_gap;
    translate([0, 0, seam_z - rim_h]) difference() {
        rbox(o, o, box_w - 2*o, box_d - 2*o, rim_h + eps, corner_r - o);
        translate([0, 0, -eps])
            rbox(o + rim_t, o + rim_t, box_w - 2*(o + rim_t), box_d - 2*(o + rim_t),
                 rim_h + 3*eps, max(0.5, corner_r - o - rim_t));
    }
}

// slot channel: two walls + floor around the card, hanging from the skin
module slot_channel() {
    translate([slot_cx - slot_len/2 - slot_wall, slot_cy - slot_gap/2 - slot_wall,
               slot_floor_z - slot_wall])
        cube([slot_len + 2*slot_wall, slot_gap + 2*slot_wall,
              seam_z - slot_floor_z + slot_wall + eps]);
}

// reader bay geometry
function bp_y1() = slot_cy + slot_gap/2 + slot_wall;   // backplate face, board side
function board_z1() = seam_z - reader_top_gap;
function board_z0() = board_z1() - reader_h;
function bay_x0() = slot_cx - reader_w/2 - reader_clear - stop_t;
function bay_x1() = slot_cx + reader_w/2 + reader_clear + stop_t;
function board_x1() = slot_cx + reader_w/2;              // header edge
function comp_y() = bp_y1() + reader_tape + reader_t;    // component side
function hdr_zc() = board_z1() - hdr_z;                  // header center

// backplate (the slot's back wall, extended down), side stops, ledge
module reader_bay() {
    z0 = board_z0() - ledge_t;
    w = bay_x1() - bay_x0();
    translate([bay_x0(), bp_y1() - slot_wall, z0])
        cube([w, slot_wall, seam_z - z0 + eps]);
    for (x = [bay_x0(), bay_x1() - stop_t])
        translate([x, bp_y1() - eps, z0])
            cube([stop_t, stop_d + eps, seam_z - z0 + eps]);
    translate([bay_x0(), bp_y1() - eps, z0])
        cube([w, stop_d + eps, ledge_t]);
}
// the right stop's cut-out: the header's pins and plugs go through
module reader_hdr_cut() {
    translate([bay_x1() - stop_t - 1, bp_y1(), hdr_zc() - hdr_len/2 - stop_cut])
        cube([stop_t + 2, stop_d + 1, hdr_len + 2*stop_cut]);
}

module cover() {
    difference() {
        union() {
            top_skin();
            rim();
            for (p = boss_pos)
                translate([p[0], p[1], boss_z0])
                    cylinder(d = boss_d, h = seam_z - boss_z0 + eps, $fn = fn);
            slot_channel();
            reader_bay();
            for (h = oled_holes)
                translate(concat(oled_pt(h[0], h[1]), [seam_z - oled_post_h]))
                    cylinder(d = oled_post_d, h = oled_post_h + eps, $fn = fn);
        }
        reader_hdr_cut();
        // card slot + entry chamfer
        translate([slot_cx - slot_len/2, slot_cy - slot_gap/2, slot_floor_z])
            cube([slot_len, slot_gap, slot_depth + eps]);
        hull() {
            translate([slot_cx - slot_len/2 - slot_ch, slot_cy - slot_gap/2 - slot_ch, box_h])
                cube([slot_len + 2*slot_ch, slot_gap + 2*slot_ch, eps]);
            translate([slot_cx - slot_len/2, slot_cy - slot_gap/2, box_h - slot_ch])
                cube([slot_len, slot_gap, eps]);
        }
        // OLED window: visible area + margin, chamfered on top
        let (wx0 = oled_x0 + oled_va[0] - win_margin,
             wx1 = oled_x0 + oled_va[0] + oled_va[2] + win_margin,
             wy0 = oled_y1 - oled_va[1] - oled_va[3] - win_margin,
             wy1 = oled_y1 - oled_va[1] + win_margin) {
            translate([wx0, wy0, seam_z - eps]) cube([wx1 - wx0, wy1 - wy0, top_t + 2*eps]);
            hull() {
                translate([wx0 - win_ch, wy0 - win_ch, box_h])
                    cube([wx1 - wx0 + 2*win_ch, wy1 - wy0 + 2*win_ch, eps]);
                translate([wx0, wy0, box_h - win_ch]) cube([wx1 - wx0, wy1 - wy0, eps]);
            }
        }
        // OLED pilot holes (blind, the top stays solid)
        for (h = oled_holes)
            translate(concat(oled_pt(h[0], h[1]), [seam_z - oled_post_h - eps]))
                cylinder(d = oled_pilot_d, h = oled_post_h + 1.5, $fn = fn);
        // buttons
        for (x = btn_x)
            translate([x, btn_y, seam_z - eps])
                cylinder(d = btn_d, h = top_t + 2*eps, $fn = fn);
        // recess under the icons (the color plate goes in it)
        translate([0, 0, seam_z - eps]) linear_extrude(icon_recess_t + eps) icon_recess_2d();
        // icon holes: the plate's raised glyphs come through
        for (i = [0 : 2])
            translate([btn_x[i], icon_y, seam_z + icon_recess_t - eps])
                linear_extrude(top_t - icon_recess_t + 2*eps)
                    offset(r = icon_gap, $fn = 16) _btn_icon(i);
        // insert pockets at the bottom of the bosses
        for (p = boss_pos)
            translate([p[0], p[1], boss_z0]) insert_pocket();
    }
}

/* ------------------- small parts ------------------- */

// printed plate down: the glyph tops are the visible faces
module icon_plate() {
    linear_extrude(icon_plate_t) icon_recess_2d(icon_plate_gap);
    for (i = [0 : 2])
        translate([btn_x[i], icon_y, 0])
            linear_extrude(icon_plate_t + icon_glyph_h)
                offset(delta = -icon_fit) _btn_icon(i, $tip_r = icon_tip_r);
}

// backing plate outline, logo coordinates: a rounded rectangle around the
// letters, its left edge trimmed clear of the front-left cover boss
function logo_plate_x0() = boss_pos[0][0]
    + sqrt(pow(boss_d/2 + 0.5, 2) - pow(boss_pos[0][1] - wall - logo_plate_t, 2));
module logo_plate_2d() {
    hw = logo_w/2 + logo_bold + logo_plate_m;
    hh = logo_w*logo_aspect/2 + logo_bold + logo_plate_m;
    intersection() {
        offset(r = 2, $fn = fn) square([2*hw - 4, 2*hh - 4], center = true);
        translate([logo_plate_x0() - logo_cx, -hh]) square([2*hw, 2*hh]);
    }
}

// printed plate down: the letter tops are the visible faces
module logo_piece() {
    linear_extrude(logo_plate_t) logo_plate_2d();
    linear_extrude(logo_plate_t + wall + logo_proud) offset(delta = -logo_fit) logo_shape();
}

/* ------------------- dummy components (views and checks) ------------------- */

module card() {
    translate([slot_cx - 27, slot_cy - 0.38, slot_floor_z]) cube([54, 0.76, 85.6]);
}

module reader_board() {
    translate([slot_cx - reader_w/2, bp_y1() + reader_tape, board_z0()])
        cube([reader_w, reader_t, reader_h]);
    // the four Dupont plugs on the right-angle header
    translate([board_x1() - hdr_inset, comp_y() + 0.1, hdr_zc() - hdr_len/2])
        cube([plug_len, 2.54, hdr_len]);
}
// components and header body on the board; plugs and wire bends past its edge
module reader_keepout() {
    translate([slot_cx - reader_w/2, comp_y(), board_z0()])
        cube([reader_w, reader_comp_t, reader_h]);
    translate([board_x1() - hdr_inset, comp_y(), hdr_zc() - hdr_len/2 - 1])
        cube([plug_len + plug_bend, reader_comp_t + 2, hdr_len + 2]);
}

module oled_module() {
    zp = seam_z - oled_post_h - oled_pcb_t;
    translate([oled_x0, oled_y1 - oled_d, zp]) cube([oled_w, oled_d, oled_pcb_t]);
    // glass
    translate(concat(oled_pt(5.0, 31.2), [zp + oled_pcb_t])) cube([89.5, 29.8, oled_glass_t]);
}
// back components + 2x8 header + Dupont plugs and wire bends below the PCB
module oled_keepout() {
    zp = seam_z - oled_post_h - oled_pcb_t;
    translate([oled_x0, oled_y1 - oled_d, zp - 2.5]) cube([oled_w, oled_d, 2.5]);
    translate(concat(oled_pt(94.5, 27), [zp - 28.5])) cube([6, 21, 28.5]);
}

module pi_board() {
    translate([pi_x0, pi_y0, pi_z0]) cube([pi_l, pi_wd, 1.6]);
    // USB x2 + Ethernet (left end after the 180° turn)
    translate([pi_x0 - 2.1, pi_y0 + 2, pi_z0 + 1.6]) cube([23.1, 53, 16]);
    // GPIO header
    translate([pi_x0 + 27.1, pi_y0 + 0.5, pi_z0 + 1.6]) cube([50.8, 5, 8.5]);
}
// Dupont plugs on the GPIO + wires, micro-USB plug at the back
module pi_keepout() {
    translate([pi_x0 + 26, pi_y0, pi_z0 + 10]) cube([53, 7, 26]);
    translate([pi_x0 + pi_l - 10.6 - 6, pi_y0 + pi_wd, pi_z0 - 1]) cube([12, 20, 10]);
}

// 12 mm button: body, lugs and wires under the skin
module button_keepout() {
    for (x = btn_x) translate([x, btn_y, seam_z - 26]) cylinder(d = 14, h = 26, $fn = fn);
}
module button_caps() {
    for (x = btn_x) translate([x, btn_y, box_h]) cylinder(d = 10, h = 2, $fn = fn);
}

module usbc_keepout() {
    translate([usbc_x - 10, box_d - wall - 16, usbc_z - 6]) cube([20, 16, 12]);
}

// mounted on the cover / in the tray
module cover_components() {
    color("SteelBlue") card();
    color("Firebrick") reader_board();
    color("DimGray") oled_module();
    color("Silver") button_caps();
}
module tray_components() {
    color("ForestGreen") pi_board();
}

/* ------------------- rendering ------------------- */

// plate against the wall's inside face, letter tops logo_proud out of the front
module logo_in_place() {
    translate([logo_cx, wall + logo_plate_t, logo_cz]) rotate([90, 0, 0]) logo_piece();
}
// plate against the recess ceiling, glyph tops icon_proud above the top
module icon_plate_in_place() {
    translate([0, 0, seam_z + icon_recess_t - icon_plate_t]) icon_plate();
}

module assembly(lift = 0) {
    color("WhiteSmoke") tray();
    color("Black") logo_in_place();
    tray_components();
    translate([0, 0, lift]) {
        color("Gainsboro") cover();
        color("DarkOrange") icon_plate_in_place();
        cover_components();
    }
}

if (part == "tray") {
    tray();
} else if (part == "cover") {
    rotate([180, 0, 0]) translate([0, 0, -box_h]) cover();
} else if (part == "icon_plate") {
    icon_plate();
} else if (part == "logo") {
    logo_piece();
} else if (part == "assembly") {
    assembly();
} else if (part == "exploded") {
    assembly(lift = 70);
}
