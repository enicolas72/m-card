use <../mcard.scad>
what = "";
cut_x = 36;
// section at x = cut_x seen from the left: X = 96 - y (front on the right), Y = z
module sec() { projection(cut = true) multmatrix([[0,-1,0,96],[0,0,1,0],[1,0,0,-cut_x],[0,0,0,1]]) children(); }
if (what == "s_tray") sec() tray();
if (what == "s_cover") sec() cover();
if (what == "s_card") sec() card();
if (what == "s_reader") sec() reader_board();
// top view: the cover cut just under its top face
if (what == "t_cover") projection(cut = true) translate([0, 0, -49.6]) cover();
if (what == "t_outline") projection() hull() tray();
