{
  description = "Nix flake for Formie.";

  inputs.nixpkgs.url = "nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }: let
    supportedSystems = [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];

    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; });

  in rec {
    packages = forAllSystems (system: let
      pkgs = nixpkgsFor.${system};
    in {
      default = pkgs.stdenv.mkDerivation {
        pname = "formie";
        version = "v3.2";

        src = ./.;
        buildInputs = with pkgs.python312Packages; [
          flask
          flask_sqlalchemy
          passlib
          argon2-cffi
        ];
      };
    });

    devShells = forAllSystems (system: {
      default = packages.${system}.default.overrideAttrs (finalAttrs: previousAttrs: {
        nativeBuildInputs = [ nixpkgsFor.${system}.black ];
      });
    });
  };
}
