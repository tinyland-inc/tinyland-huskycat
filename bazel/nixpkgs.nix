# bazel/nixpkgs.nix
# Bridge between Bazel and Nix: reads flake.lock to derive the exact
# nixpkgs revision, ensuring both build systems use identical packages.
#
# Used by rules_nixpkgs nix_repo.file() extension in MODULE.bazel.
# When nix flake update is run, this automatically picks up the new pin.

let
  lock = builtins.fromJSON (builtins.readFile ../flake.lock);
  nixpkgsNodeName = lock.nodes.${lock.root}.inputs.nixpkgs;
  nixpkgsLock = lock.nodes.${nixpkgsNodeName}.locked;
in
import (builtins.fetchTarball {
  url = "https://github.com/${nixpkgsLock.owner}/${nixpkgsLock.repo}/archive/${nixpkgsLock.rev}.tar.gz";
  sha256 = nixpkgsLock.narHash;
}) {}
