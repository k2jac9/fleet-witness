{ demoFor }:
{ config, lib, pkgs, ... }:
let
  cfg = config.services.fleetWitnessDemo;
  demo = demoFor pkgs.stdenv.hostPlatform.system;
  # A single DNS hostname only: no scheme, port, wildcard, path or Caddy syntax.
  validHost = host:
    builtins.stringLength host <= 253
    && builtins.length (lib.splitString "." host) >= 2
    && builtins.all (label:
      builtins.stringLength label <= 63
      && builtins.match "[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?" label != null
    ) (lib.splitString "." host)
    && builtins.match ".*[a-zA-Z].*" (lib.last (lib.splitString "." host)) != null;
in {
  options.services.fleetWitnessDemo = {
    enable = lib.mkEnableOption "read-only Fleet Witness scripted replay";
    publicHostName = lib.mkOption {
      type = lib.types.nullOr (lib.types.addCheck lib.types.str validHost);
      default = null;
      example = "fleet.example.org";
      description = "Explicit DNS hostname enabling public Caddy HTTPS; null keeps the viewer loopback-only.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.fleet-witness-demo = {
      description = "Fleet Witness read-only scripted replay";
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        ExecStart = "${demo}/bin/fleet-witness-demo";
        DynamicUser = true;
        User = "fleet-witness-demo";
        Restart = "on-failure";
        RestartSec = "5s";
        NoNewPrivileges = true;
        CapabilityBoundingSet = "";
        AmbientCapabilities = "";
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        PrivateDevices = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectControlGroups = true;
        RestrictSUIDSGID = true;
        LockPersonality = true;
        RestrictRealtime = true;
        RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" ];
        IPAddressDeny = "any";
        IPAddressAllow = "localhost";
        InaccessiblePaths = [ "/nix/var/nix" ];
        UMask = "0077";
      };
    };

    services.caddy = lib.mkIf (cfg.publicHostName != null) {
      enable = true;
      openFirewall = true;
      virtualHosts.${cfg.publicHostName}.extraConfig = ''
        reverse_proxy 127.0.0.1:8765
      '';
    };
  };
}
