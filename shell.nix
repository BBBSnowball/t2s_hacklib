{ pkgs ? import <nixpkgs> {} }:
let
    py = pkgs.python3.withPackages (p: with p; [
        numpy
        matplotlib
        opencv4
        pillow
        #(opencv4.override {enableGtk3 = true; enableGtk2 = true;})
    ]);
in
with pkgs;
mkShell {
    packages = [
        py
        v4l-utils
    ];
}