{ pkgs, modulesPath, deploymentSource, ... }:
{
  imports = [ (modulesPath + "/virtualisation/google-compute-image.nix") ];

  system.stateVersion = "26.05";
  networking.hostName = "fleet-gcp";
  # Upstream GCE disables the guest firewall by default. Keep SSH only until
  # publicHostName explicitly enables Caddy; GCP must independently restrict SSH to IAP.
  networking.firewall.enable = true;
  security.googleOsLogin.enable = true;
  services.openssh.settings = {
    PasswordAuthentication = false;
    KbdInteractiveAuthentication = false;
    PermitRootLogin = "no";
  };
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  # Trusted-operator tools used by the collection and update runbooks.
  environment.systemPackages = [ pkgs.git pkgs.python3 pkgs.curl ];

  services.fleetWitnessDemo.enable = true;
  services.fleetWitnessFleet = {
    enable = true;
    workers = [ "w-runtime" "w-viewer" "w-scenario" "w-review" ];
  };

  # Retain the exact public source (including its lock) for recovery/rebuilds.
  # Nix store paths are public: never place credentials in the source tree.
  environment.etc."fleet-witness/source".source = deploymentSource;
  virtualisation.googleComputeImage.configFile = toString (pkgs.writeText "fleet-witness-rebuild.nix" ''
    # The generic GCE configuration would silently drop Fleet Witness.
    # Rebuild this image's source, or use an explicitly reviewed updated checkout:
    # sudo nixos-rebuild switch --flake /etc/fleet-witness/source#fleet-gcp
    throw "Fleet Witness requires an explicit flake rebuild: nixos-rebuild switch --flake /etc/fleet-witness/source#fleet-gcp"
  '');
}
