{
  description = "Fleet Witness offline development workers";

  # Verified nixos-26.05 revision; generate a real flake.lock on a Nix host.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33";

  outputs = { nixpkgs, ... }:
    let
      lib = nixpkgs.lib;
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forSystems = lib.genAttrs systems;
      # Only reviewed project inputs enter the immutable worker snapshot.
      # Exclude symlinks, hidden files, Git state, runs, and Python caches.
      workerSource = lib.cleanSourceWith {
        src = ./.;
        filter = path: type:
          let
            relative = lib.removePrefix (toString ./. + "/") (toString path);
            parts = lib.splitString "/" relative;
            top = builtins.head parts;
            base = builtins.baseNameOf path;
          in
            type != "symlink"
            && !(lib.hasPrefix "." base)
            && base != "__pycache__"
            && !(lib.hasSuffix ".pyc" base)
            && (builtins.elem top [ "fleet_witness" "tests" "nix" "fleet" "scripts" "docs" ]
              || builtins.elem relative [ "AGENTS.md" "README.md" ]);
      };
    in {
      nixosModules.fleet = import ./nix/fleet.nix {
        inherit workerSource;
        nixpkgsPath = nixpkgs.outPath;
      };

      devShells = forSystems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in { default = pkgs.mkShell {
          packages = [ pkgs.python3 pkgs.nodejs pkgs.git ];
        }; });

      checks.x86_64-linux.offline-tests =
        let pkgs = nixpkgs.legacyPackages.x86_64-linux;
        in pkgs.runCommand "fleet-witness-offline-tests" {
          nativeBuildInputs = [ pkgs.bash pkgs.coreutils pkgs.python3 pkgs.nodejs pkgs.git ];
        } ''
          bash ${./nix/offline-task.sh} ${workerSource} "$TMPDIR/task"
          mkdir -p "$out"
          cp -R "$TMPDIR/task/results/." "$out/"
        '';
    };
}
