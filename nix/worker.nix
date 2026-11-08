{ workerSource }:
{ pkgs, ... }:
{
  system.stateVersion = "26.05";
  networking.useDHCP = false;
  services.openssh.enable = false;
  nix.enable = false;
  users.groups.worker.gid = 1000;
  users.users.worker = {
    isNormalUser = true;
    uid = 1000;
    group = "worker";
    home = "/work";
    createHome = false;
    hashedPassword = "!";
  };

  # A container-level mount survives task completion until container teardown.
  fileSystems."/work" = {
    device = "tmpfs";
    fsType = "tmpfs";
    options = [ "size=512M" "mode=0700" "uid=1000" "gid=1000" "nosuid" "nodev" ];
  };
  systemd.services.fleet-task = {
    description = "Offline tests and scripted demo (no model backend)";
    wantedBy = [ "multi-user.target" ];
    unitConfig.RequiresMountsFor = [ "/work" ];
    path = [ pkgs.bash pkgs.coreutils pkgs.python3 pkgs.nodejs pkgs.git ];
    environment = {
      HOME = "/work";
      TMPDIR = "/work";
      PYTHONDONTWRITEBYTECODE = "1";
    };
    serviceConfig = {
      Type = "oneshot";
      User = "worker";
      Group = "worker";
      ExecStart = "${pkgs.bash}/bin/bash ${./offline-task.sh} ${workerSource} /work/task";
      TimeoutStartSec = "10min";
      TimeoutStopSec = "10s";
      KillMode = "control-group";
      RemainAfterExit = true;
      Restart = "no";
      UMask = "0077";
      NoNewPrivileges = true;
      CapabilityBoundingSet = "";
      AmbientCapabilities = "";
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ "/work" ];
      # Standard container plumbing exposes host-backed Nix sockets/profiles.
      InaccessiblePaths = [ "/nix/var/nix" ];
      PrivateNetwork = true;
      RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_INET6" ];
      PrivateDevices = true;
      ProtectKernelTunables = true;
      ProtectKernelModules = true;
      ProtectControlGroups = true;
      RestrictSUIDSGID = true;
      LockPersonality = true;
      RestrictRealtime = true;
    };
  };
}
