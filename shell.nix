{ pkgs ? import <nixpkgs> {} }:
let
    py = pkgs.python3.withPackages (p: with p; [
        numpy
        matplotlib
        pillow
        opencv4
        #(opencv4.override {enableGtk3 = true; enableGtk2 = true;})
        scikit-image
    ]);
in
with pkgs;
mkShell {
    packages = [
        py
        v4l-utils
    ];
}