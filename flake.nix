{
  description = "Fleet Witness scripted viewer and offline development workers";

  # Verified nixos-26.05 revision; flake.lock records the resolved source hash.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33";

  outputs = { self, nixpkgs, ... }:
    let
      lib = nixpkgs.lib;
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forSystems = lib.genAttrs systems;
      # The hosted application never receives worker inputs or task outputs.
      appSource = lib.cleanSourceWith {
        src = ./fleet_witness;
        filter = path: type:
          let base = builtins.baseNameOf path;
          in type != "symlink"
            && !(lib.hasPrefix "." base)
            && base != "__pycache__"
            && !(lib.hasSuffix ".pyc" base);
      };
      demoFor = system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in pkgs.runCommand "fleet-witness-demo" {
          nativeBuildInputs = [ pkgs.python3 pkgs.makeWrapper ];
        } ''
          mkdir -p "$out/lib/fleet_witness" "$out/share/fleet-witness" "$out/bin"
          cp -R ${appSource}/. "$out/lib/fleet_witness/"
          export PYTHONPATH="$out/lib" PYTHONDONTWRITEBYTECODE=1
          # The database and random synthetic signing key stay in the build sandbox.
          python -m fleet_witness demo --output "$TMPDIR/demo" --seed 42
          for asset in index.html styles.css app.js replay.json; do
            cp "$TMPDIR/demo/$asset" "$out/share/fleet-witness/$asset"
          done
          makeWrapper ${pkgs.python3}/bin/python "$out/bin/fleet-witness-demo" \
            --set PYTHONPATH "$out/lib" --set PYTHONDONTWRITEBYTECODE 1 \
            --add-flags "-m fleet_witness serve --directory $out/share/fleet-witness --port 8765"
        '';
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

      nixosModules.demo = import ./nix/demo.nix { inherit demoFor; };

      packages = forSystems (system: { demo = demoFor system; });

      nixosConfigurations.fleet-gcp = lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs.deploymentSource = self.outPath;
        modules = [ self.nixosModules.fleet self.nixosModules.demo ./nix/hosts/gcp.nix ];
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
