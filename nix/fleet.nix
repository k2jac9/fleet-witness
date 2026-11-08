{ workerSource, nixpkgsPath }:
{ config, lib, ... }:
let
  cfg = config.services.fleetWitnessFleet;
  validName = name: builtins.match "[a-z][a-z0-9-]{0,10}" name != null;
  # Validate before names become systemd instance names or container paths.
  names = map (name:
    if validName name then name
    else throw "fleetWitnessFleet worker name '${name}' must match [a-z][a-z0-9-]{0,10}"
  ) cfg.workers;
in {
  options.services.fleetWitnessFleet = {
    enable = lib.mkEnableOption "ephemeral offline Fleet Witness workers";
    workers = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      example = [ "w-runtime" "w-viewer" ];
      description = "Unique container names, each 1–11 lower-case letters/digits/hyphens, starting with a letter.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [{
      assertion = builtins.length names == builtins.length (lib.unique names);
      message = "fleetWitnessFleet worker names must be unique";
    }];
    boot.enableContainers = true;
    containers = lib.genAttrs names (_: {
      nixpkgs = nixpkgsPath;
      autoStart = false;
      # Boot readiness waits for the ten-minute oneshot; allow startup overhead.
      timeoutStartSec = "12min";
      ephemeral = true;
      privateUsers = "pick";
      privateNetwork = true;
      config = import ./worker.nix { inherit workerSource; };
    });
    # nixos-containers uses nspawn --keep-unit: these are aggregate host limits.
    systemd.services = lib.genAttrs (map (name: "container@${name}") names) (_: {
      serviceConfig = {
        CPUQuota = "100%";
        MemoryMax = "1G";
        MemorySwapMax = "0";
        TasksMax = 256;
        RuntimeMaxSec = "15min";
        Restart = lib.mkForce "no";
        RestartForceExitStatus = lib.mkForce [ ];
      };
    });
  };
}
