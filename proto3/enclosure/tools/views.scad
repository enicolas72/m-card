use <../mcard.scad>
view = "";
if (view == "under") {
    color("Gainsboro") cover();
    color("Firebrick") reader_board();
    color("DimGray") oled_module();
}
if (view == "section") {
    difference() {
        union() {
            color("WhiteSmoke") tray();
            color("Gainsboro") cover();
            color("SteelBlue") card();
            color("Firebrick") reader_board();
            color("ForestGreen") pi_board();
        }
        translate([-1, -50, -50]) cube([36, 300, 300]);
    }
}
